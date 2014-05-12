#include <gio/gio.h>
#include <json-glib/json-glib.h>
#include <libsoup/soup.h>

static void
request_ready (GObject *session,
               GAsyncResult *res,
               gpointer user_data)
{
  g_warning ("READY");
}

static void
send_change (JsonNode *root)
{
  gsize          len;
  gchar         *data;
  JsonGenerator *gen = json_generator_new ();
  SoupSession   *ses = soup_session_new ();
  SoupMessage   *msg = soup_message_new ("POST", "http://localhost:8181/submit_change");

  json_generator_set_root (gen, root);
  data = json_generator_to_data (gen, &len);

  soup_message_set_request (msg,
                            "application/json",
                            SOUP_MEMORY_TAKE,
                            data,
                            len);

  soup_session_send_async (ses, msg, NULL, request_ready, NULL);

  g_object_unref (msg);

/* FIXME: Leaking here, for some reason unreffing this kicks a segfault
  g_object_unref (gen); */
}

static void
changed_cb (GSettings *settings, gchar *key, gpointer user_data)
{
  JsonNode      *root;
  JsonNode      *value_node = NULL;
  JsonArray     *array     = NULL;
  gchar         *schema_id = NULL;

  GVariant *value = g_settings_get_value (settings, key);
  g_object_get (settings, "schema-id", &schema_id, NULL);

  value_node = json_gvariant_serialize (value);

  array = json_array_new ();
  root  = json_node_new (JSON_NODE_ARRAY);

  json_array_add_string_element (array, schema_id);
  json_array_add_string_element (array, key);
  json_array_add_string_element (array, g_variant_get_type_string (value));
  json_array_add_element (array, value_node);
  json_node_init_array (root, array);

  /* TODO: Feed this to some local web service */
  send_change (root);

  g_variant_unref (value);

  json_node_free (root);
  json_array_unref (array);
  json_node_free (value_node);

  g_free (schema_id);
  return;
}

gint
main (gint argc, gchar **argv)
{
  gchar **nonr, **reloc;
  gint i;
  GSettingsSchemaSource *src = g_settings_schema_source_get_default ();

  g_settings_schema_source_list_schemas (src, TRUE, &nonr, &reloc);

  for (i = 0; nonr[i] != NULL; i++)
  {
    GSettingsSchema *sch      = g_settings_schema_source_lookup (src, nonr[i], TRUE);
    GSettings       *settings = g_settings_new_with_path (nonr[i], g_settings_schema_get_path (sch));

    g_signal_connect (settings, "changed", G_CALLBACK(changed_cb), NULL);
    g_settings_schema_unref (sch);
  }

  g_main_loop_run (g_main_loop_new (NULL, TRUE));
  return 0;
}
