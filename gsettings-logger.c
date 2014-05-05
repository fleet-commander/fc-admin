#include <gio/gio.h>
#include <json-glib/json-glib.h>

static void
changed_cb (GSettings *settings, gchar *key, gpointer user_data)
{
  JsonNode      *root;
  JsonNode      *value_node = NULL;
  JsonArray     *array     = NULL;
  gchar         *schema_id = NULL;
  JsonGenerator *gen       = NULL;
  gsize          len;
  gchar         *data;


  GVariant *value = g_settings_get_value (settings, key);
  g_object_get (settings, "schema-id", &schema_id, NULL);

  value_node = json_gvariant_serialize (value);
  gen =  json_generator_new ();

  array = json_array_new ();
  root  = json_node_new (JSON_NODE_ARRAY);

  json_array_add_string_element (array, schema_id);
  json_array_add_string_element (array, key);
  json_array_add_string_element (array, g_variant_get_type_string (value));
  json_array_add_element (array, value_node);
  json_node_init_array (root, array);

  json_generator_set_root (gen, root);
  data = json_generator_to_data (gen, &len);

  /* TODO: Feed this to some local web service */
  g_warning (data);

  g_variant_unref (value);

  json_node_free (root);
  json_array_unref (array);
  json_node_free (value_node);

  g_free (schema_id);
  g_free (data);

/* FIXME: Leaking here, for some reason unreffing this kicks a segfault
  g_object_unref (gen); */
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
