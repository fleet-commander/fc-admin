/*
 * Copyright (C) 2014 Red Hat, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the licence, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program; if not, see <http://www.gnu.org/licenses/>.
 *
 * Authors: Alberto Ruiz <aruiz@gnome.org>
 *          Matthew Barnes <mbarnes@redhat.com>
 */

/* This monitors the ca.desrt.dconf.Writer interface directly for "Notify"
 * signals.  This allows us to capture change notifications for both fixed
 * path AND relocatable GSettings schemas.
 *
 * Logging changes for fixed-path schemas is trivial, because the path is
 * encoded into the schema itself.  So given the changed path, it's just a
 * reverse-lookup to find the fixed-path schema.
 *
 * Logging changes for relocatable schemas is much more complex, because it
 * involves guessing.  It's what most of the data structures below are for.
 * We use a process of elimination to determine which relocatable schema is
 * in use at a particular path, much like the game of Clue.
 *
 * There's a fixed set of relocatable schemas, each of which defines a set
 * of keys.  As we receive change notifications for a path which we know is
 * using a relocatable schema, we accumulate a set of changed key names for
 * that path which serve as clues.
 *
 * On the first notification for such a path, we evalute ALL relocatable
 * schemas and select candidates which satisfy the initial changed key set.
 * This can yield an ambigous result if multiple relocatable schemas define
 * the key(s) we know have changed.  Only one of the candidate schemas is
 * the correct one, but regardless we create a GSettings instance for each
 * candidate schema at the same path.  (It turns out GLib doesn't care; its
 * enforcement of relocatable schemas is surprisingly weak.)
 *
 * This CAN yield bogus change entries in the log (right key, wrong schema).
 *
 * As the changed key set for that path expands from further notifications,
 * we reexamine the candidate schemas for that path and eliminate those that
 * no longer satisfy the (expanded) changed key set.  When only one candidate
 * remains, we can conclude with certainty which relocatable schema is in use
 * at that path.
 *
 * Mr. Green, in the Observatory, with a lead pipe.
 **/

#include <string.h>
#include <gio/gio.h>
#include <libsoup/soup.h>
#include <json-glib/json-glib.h>

/* path_to_known_settings : { path : GSettings }
 *
 * This is for GSettings with fixed-path schemas and
 * also relocatable schemas which we're certain of. */
static GHashTable *path_to_known_settings;

/* path_to_reloc_settings : { path : { GSettingsSchema : GSettings } }
 *
 * This is for GSettings with relocatable schemas which we're UNCERTAIN of.
 * The goal is to narrow the candidate set for a particular path to one and
 * then move that last GSettings instance to 'path_to_known_settings'. */
static GHashTable *path_to_reloc_settings;

/* path_to_changed_keys : { path : ( set of keys ) }
 *
 * The set of keys we've observed changes to, by path. */
static GHashTable *path_to_changed_keys;

/* relocatable_schemas : [ GSettingsSchema ] */
static GPtrArray *relocatable_schemas;

#define DCONF_BUS_NAME        "ca.desrt.dconf"
#define DCONF_OBJECT_PATH     "/ca/desrt/dconf/Writer/user"
#define DCONF_INTERFACE_NAME  "ca.desrt.dconf.Writer"

static GDBusConnection *global_session_bus;
static guint dconf_watch_name_id;
static guint dconf_subscription_id;

#define POST_URL  "http://localhost:8181/submit_change"

static SoupSession *global_soup_session;

static void
post_change_entry_cb (GObject *source_object,
                      GAsyncResult *result,
                      gpointer user_data)
{
	GInputStream *input_stream;
	GError *local_error = NULL;

	input_stream = soup_session_send_finish (
		SOUP_SESSION (source_object), result, &local_error);

	if (local_error != NULL) {
		g_warning ("POST failed: %s", local_error->message);
		g_error_free (local_error);
	} else {
		g_debug ("POST successful");
	}

	g_clear_object (&input_stream);
}

static void
post_change_entry (const gchar *abs_key,
                   const gchar *schema_id,
                   GVariant *value)
{
	JsonNode *root;
	JsonNode *node;
	JsonObject *object;
	JsonGenerator *generator;
	SoupMessage *message;
	gchar *data;
	gsize data_length;

	object = json_object_new ();
	json_object_set_string_member (object, "key", abs_key);
	json_object_set_string_member (object, "schema", schema_id);

	/* JsonObject takes ownership of JsonNode. */
	node = json_gvariant_serialize (value);
	json_object_set_member (object, "value", node);

	root = json_node_new (JSON_NODE_OBJECT);
	json_node_init_object (root, object);

	generator = json_generator_new ();
	json_generator_set_root (generator, root);
	data = json_generator_to_data (generator, &data_length);
	g_object_unref (generator);

	g_debug ("POST %s\n%s", POST_URL, data);

	message = soup_message_new (SOUP_METHOD_POST, POST_URL);
	soup_message_set_request (
		message, "application/json",
		SOUP_MEMORY_TAKE, data, data_length);
	soup_session_send_async (
		global_soup_session, message,
		NULL, post_change_entry_cb, NULL);
	g_object_unref (message);

	json_node_free (root);
	json_object_unref (object);
}

static void
settings_changed_cb (GSettings *settings,
                     const gchar *key)
{
	GVariant *value;
	gchar *schema_id;
	gchar *abs_key;
	gchar *path;

	value = g_settings_get_value (settings, key);

	g_object_get (settings, "schema-id", &schema_id, "path", &path, NULL);

	g_debug ("GSettings::changed('%s', '%s') at %s", schema_id, key, path);

	abs_key = g_build_path ("/", path, key, NULL);

	post_change_entry (abs_key, schema_id, value);

	g_free (abs_key);
	g_free (schema_id);
	g_free (path);

	g_variant_unref (value);
}

static GSettings *
new_settings_for_schema (GSettingsSchema *schema,
                         const gchar *path)
{
	GSettings *settings;

	settings = g_settings_new_full (schema, NULL, path);

	g_signal_connect (
		settings, "changed",
		G_CALLBACK (settings_changed_cb), NULL);

	return settings;
}

static gboolean
schema_has_all_keys (GSettingsSchema *schema,
                     const gchar * const *keys)
{
	guint ii;

	g_return_val_if_fail (keys != NULL, TRUE);

	for (ii = 0; keys[ii] != NULL; ii++) {
		if (!g_settings_schema_has_key (schema, keys[ii]))
			return FALSE;
	}

	return TRUE;
}

static GList *
relocatable_schemas_lookup (const gchar * const *keys)
{
	GQueue matches = G_QUEUE_INIT;
	guint ii;

	for (ii = 0; ii < relocatable_schemas->len; ii++) {
		GSettingsSchema *schema;

		schema = g_ptr_array_index (relocatable_schemas, ii);

		if (schema_has_all_keys (schema, keys))
			g_queue_push_tail (&matches, schema);
	}

	return g_queue_peek_head_link (&matches);
}

static guint
path_to_reloc_settings_add (const gchar *path,
                            const gchar * const *keys)
{
	GHashTable *reloc_settings;
	GList *list, *link;
	guint n_schemas = 0;

	g_return_if_fail (path != NULL);

	list = relocatable_schemas_lookup (keys);

	reloc_settings = g_hash_table_lookup (path_to_reloc_settings, path);

	/* Avoid leaving an empty hash table so that
	 * path_to_reloc_settings_has_path() works. */

	if (reloc_settings == NULL && list != NULL) {
		reloc_settings = g_hash_table_new_full (
			(GHashFunc) g_direct_hash,
			(GEqualFunc) g_direct_equal,
			(GDestroyNotify) g_settings_schema_unref,
			(GDestroyNotify) g_object_unref);
		g_hash_table_replace (
			path_to_reloc_settings,
			g_strdup (path), reloc_settings);
	}

	g_assert (reloc_settings != NULL || list == NULL);

	if (list == NULL)
		g_debug (">>> No candidate schemas!");

	for (link = list; link != NULL; link = g_list_next (link)) {
		GSettingsSchema *schema = link->data;

		if (!g_hash_table_contains (reloc_settings, schema)) {
			/* XXX We create the GSettings instance early
			 *     enough for it to apparently pick up and
			 *     log the dconf change notification we're
			 *     handling.  At least I think.  Should
			 *     test this more thoroughly to be sure. */
			g_debug (
				">>> Adding candidate schema '%s'",
				g_settings_schema_get_id (schema));
			g_hash_table_replace (
				reloc_settings,
				g_settings_schema_ref (schema),
				new_settings_for_schema (schema, path));
		}
	}

	if (reloc_settings != NULL)
		n_schemas = g_hash_table_size (reloc_settings);

	g_list_free (list);

	return n_schemas;
}

static guint
path_to_reloc_settings_audit (const gchar *path,
                              const gchar * const *keys)
{
	GHashTable *reloc_settings;
	GList *list, *link;
	guint n_schemas = 0;

	g_return_val_if_fail (path != NULL, 0);

	/* Remove any GSettings instances with schemas that are in
	 * conflict with our key change observations from dconf.  The
	 * hope is to observe enough key changes on a particular path
	 * that we can discover through elimination which relocatable
	 * schema is in use at that path. */

	reloc_settings = g_hash_table_lookup (path_to_reloc_settings, path);

	if (reloc_settings == NULL)
		goto exit;

	list = g_hash_table_get_keys (reloc_settings);

	for (link = list; link != NULL; link = g_list_next (link)) {
		GSettingsSchema *schema = link->data;

		if (!schema_has_all_keys (schema, keys)) {
			g_debug (
				">>> Removing candidate schema '%s'",
				g_settings_schema_get_id (schema));
			g_hash_table_remove (reloc_settings, schema);
		}
	}

	g_list_free (list);

	n_schemas = g_hash_table_size (reloc_settings);

	/* Remove an empty hash table so that
	 * path_to_reloc_settings_has_path() works. */
	if (n_schemas == 0)
		g_hash_table_remove (path_to_reloc_settings, path);

exit:
	return n_schemas;
}

static void
path_to_reloc_settings_elect (const gchar *path)
{
	GHashTable *reloc_settings;
	GHashTableIter iter;
	gpointer settings;

	g_return_if_fail (path != NULL);

	reloc_settings = g_hash_table_lookup (path_to_reloc_settings, path);
	g_return_if_fail (reloc_settings != NULL);

	/* There should only be one item in the hash table,
	 * but we'll interate over the hash table regardless. */
	g_warn_if_fail (g_hash_table_size (reloc_settings) == 1);

	g_hash_table_iter_init (&iter, reloc_settings);

	while (g_hash_table_iter_next (&iter, NULL, &settings)) {
		gchar *schema_id;

		g_object_get (settings, "schema-id", &schema_id, NULL);
		g_debug (">>> Electing candidate schema '%s'", schema_id);
		g_free (schema_id);

		g_hash_table_replace (
			path_to_known_settings,
			g_strdup (path),
			g_object_ref (settings));
	}

	g_hash_table_remove (path_to_reloc_settings, path);
}

static gboolean
path_to_reloc_settings_has_path (const gchar *path)
{
	g_return_val_if_fail (path != NULL, FALSE);

	return g_hash_table_contains (path_to_reloc_settings, path);
}

static GHashTable *
path_to_changed_keys_internal_lookup (const gchar *path)
{
	GHashTable *changed_keys;

	g_return_val_if_fail (path != NULL, NULL);

	changed_keys = g_hash_table_lookup (path_to_changed_keys, path);

	if (changed_keys == NULL) {
		changed_keys = g_hash_table_new (
			(GHashFunc) g_str_hash,
			(GEqualFunc) g_str_equal);
		g_hash_table_replace (
			path_to_changed_keys,
			g_strdup (path), changed_keys);
	}

	return changed_keys;
}

static void
path_to_changed_keys_add (const gchar *path,
                          const gchar * const *keys)
{
	GHashTable *changed_keys;
	gint ii;

	g_return_if_fail (path != NULL);
	g_return_if_fail (keys != NULL);

	changed_keys = path_to_changed_keys_internal_lookup (path);
	g_return_if_fail (changed_keys != NULL);

	for (ii = 0; keys[ii] != NULL; ii++) {
		const gchar *key = g_intern_string (keys[ii]);
		g_hash_table_add (changed_keys, (gpointer) key);
	}
}

static gchar **
path_to_changed_keys_lookup (const gchar *path)
{
	GHashTable *changed_keys;

	changed_keys = path_to_changed_keys_internal_lookup (path);
	g_return_val_if_fail (changed_keys != NULL, NULL);

	return (gchar **) g_hash_table_get_keys_as_array (changed_keys, NULL);
}

static void
update_schema_candidates (const gchar *path)
{
	const gchar * const *const_keys;
	gchar **keys;
	guint n_schemas;

	keys = path_to_changed_keys_lookup (path);
	g_return_if_fail (keys != NULL);

	/* Just for convenience. */
	const_keys = (const gchar * const *) keys;

	/* For the first change notification on this path, we evaluate all
	 * relocatable schemas for valid candidates.  For subsequent change
	 * notifications on this path, the candidate set can only reduce.
	 * Once the candidate set reduces to one, we can be certain which
	 * relocatable schema is in use and move the GSettings instance to
	 * "paths_to_known_settings" and forgo all this bookkeeping. */

	if (path_to_reloc_settings_has_path (path))
		n_schemas = path_to_reloc_settings_audit (path, const_keys);
	else
		n_schemas = path_to_reloc_settings_add (path, const_keys);

	if (n_schemas == 1)
		path_to_reloc_settings_elect (path);
}

static void
dconf_writer_notify_cb (GDBusConnection *session_bus,
                        const gchar *sender_name,
                        const gchar *object_path,
                        const gchar *interface_name,
                        const gchar *signal_name,
                        GVariant *parameters,
                        gpointer unused)
{
	gchar **keys = NULL;
	gchar *debug_keys;
	gchar *path;
	gint ii;

	/* Parameters are (string: path, array(string): keys, string: tag)
	 * but 'keys' are only relevant if 'path' has a trailing slash.
	 * Otherwise 'path' is actually path/key and 'keys' is empty. */

	g_variant_get_child (parameters, 0, "s", &path);
	g_return_if_fail (path != NULL);

	if (g_str_has_suffix (path, "/")) {
		g_variant_get_child (parameters, 1, "^as", &keys);
	} else {
		gchar *cp;

		/* Convert 'path/key' to 'path/' and a keys array. */
		if ((cp = strrchr (path, '/')) != NULL) {
			keys = g_new (gchar *, 2);
			keys[0] = strdup (++cp);
			keys[1] = NULL;
			*cp = '\0';
		}
	}

	g_debug (
		"dconf Notify: %s (%s)\n", path,
		g_hash_table_contains (path_to_known_settings, path) ?
		"schema known" : "schema not yet known");

	debug_keys = g_strjoinv (", ", keys);
	g_debug (">>> Keys: %s", debug_keys);
	g_free (debug_keys);

	/* Do nothing if we already know the schema at this path.
	 * Our GSettings::changed callback will record the change. */
	if (g_hash_table_contains (path_to_known_settings, path))
		goto exit;

	/* Note the keys that changed on this path.  We know a relocatable
	 * schema is in use at this path, but we can't be certain which one.
	 * However the probability of guessing right increases as the number
	 * of changed keys on this path accumulates, because we can compare
	 * the accumulated set of changed keys to the schemas' keys. */
	path_to_changed_keys_add (path, (const gchar * const *) keys);

	update_schema_candidates (path);

exit:
	g_strfreev (keys);
	g_free (path);
}

static void
dconf_bus_name_appeared_cb (GDBusConnection *session_bus,
                            const gchar *bus_name,
                            const gchar *bus_name_owner,
                            gpointer unused)
{
	/* Stash the connection so we can unsubscribe on exit. */
	g_clear_object (&global_session_bus);
	global_session_bus = g_object_ref (session_bus);

	dconf_subscription_id = g_dbus_connection_signal_subscribe (
		session_bus,
		bus_name_owner,
		DCONF_INTERFACE_NAME,
		"Notify",
		DCONF_OBJECT_PATH,
		NULL,
		G_DBUS_SIGNAL_FLAGS_NONE,
		dconf_writer_notify_cb,
		NULL, (GDestroyNotify) NULL);
}

static void
dconf_bus_name_vanished_cb (GDBusConnection *session_bus,
                            const gchar *bus_name,
                            gpointer unused)
{
	if (dconf_subscription_id > 0) {
		g_dbus_connection_signal_unsubscribe (
			session_bus, dconf_subscription_id);
		dconf_subscription_id = 0;
	}
}

gint
main (gint argc, gchar **argv)
{
	GSettingsSchemaSource *schema_source;
	GSettings *settings1;
	GSettings *settings2;
	gchar **relocatable_schema_ids;
	gchar **non_relocatable_schema_ids;
	gint ii;

	path_to_known_settings = g_hash_table_new_full (
		(GHashFunc) g_str_hash,
		(GEqualFunc) g_str_equal,
		(GDestroyNotify) g_free,
		(GDestroyNotify) g_object_unref);

	path_to_reloc_settings = g_hash_table_new_full (
		(GHashFunc) g_str_hash,
		(GEqualFunc) g_str_equal,
		(GDestroyNotify) g_free,
		(GDestroyNotify) g_hash_table_destroy);

	path_to_changed_keys = g_hash_table_new_full (
		(GHashFunc) g_str_hash,
		(GEqualFunc) g_str_equal,
		(GDestroyNotify) g_free,
		(GDestroyNotify) g_hash_table_destroy);

	relocatable_schemas = g_ptr_array_new_with_free_func (
		(GDestroyNotify) g_settings_schema_unref);

	global_soup_session = soup_session_new ();

	schema_source = g_settings_schema_source_get_default ();

	g_settings_schema_source_list_schemas (
		schema_source, TRUE,
		&non_relocatable_schema_ids,
		&relocatable_schema_ids);

	/* Populate a table of paths to GSettings instances.  We can
	 * do this up front for fixed-path schemas.  For relocatable
	 * schemas, we have to wait for a change to occur and then try
	 * to derive the schema from the path and key(s) in the change
	 * notification. */
	for (ii = 0; non_relocatable_schema_ids[ii] != NULL; ii++) {
		GSettingsSchema *schema;

		schema = g_settings_schema_source_lookup (
			schema_source, non_relocatable_schema_ids[ii], TRUE);

		if (schema != NULL) {
			const gchar *path;

			path = g_settings_schema_get_path (schema);
			g_assert (path != NULL);

			g_hash_table_replace (
				path_to_known_settings,
				g_strdup (path),
				new_settings_for_schema (schema, NULL));

			g_settings_schema_unref (schema);
		}
	}

	for (ii = 0; relocatable_schema_ids[ii] != NULL; ii++) {
		GSettingsSchema *schema;

		schema = g_settings_schema_source_lookup (
			schema_source, relocatable_schema_ids[ii], TRUE);

		if (schema != NULL) {
			/* The array takes ownership of the schema. */
			g_ptr_array_add (relocatable_schemas, schema);
		}
	}

	g_strfreev (non_relocatable_schema_ids);
	g_strfreev (relocatable_schema_ids);

	/* Listen directly to dconf's D-Bus interface so we're
	 * notified of changes on ALL paths, regardless of schema. */

	dconf_watch_name_id = g_bus_watch_name (
		G_BUS_TYPE_SESSION,
		DCONF_BUS_NAME,
		G_BUS_NAME_WATCHER_FLAGS_NONE,
		dconf_bus_name_appeared_cb,
		dconf_bus_name_vanished_cb,
		NULL, (GDestroyNotify) NULL);

	g_main_loop_run (g_main_loop_new (NULL, TRUE));

	if (dconf_subscription_id > 0) {
		g_dbus_connection_signal_unsubscribe (
			global_session_bus, dconf_subscription_id);
	}

	g_clear_object (&global_session_bus);
	g_clear_object (&global_soup_session);

	g_hash_table_destroy (path_to_known_settings);
	g_hash_table_destroy (path_to_reloc_settings);
	g_hash_table_destroy (path_to_changed_keys);
	g_ptr_array_free (relocatable_schemas, TRUE);

	return 0;
}

