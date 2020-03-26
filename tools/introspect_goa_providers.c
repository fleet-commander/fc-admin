/*
 * Copyright (C) 2016 Red Hat, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General
 * Public License along with this library; if not, see <http://www.gnu.org/licenses/>.
 */

#include <locale.h>

#include <glib.h>

#define GOA_API_IS_SUBJECT_TO_CHANGE
#define GOA_BACKEND_API_IS_SUBJECT_TO_CHANGE
#include <goabackend/goabackend.h>

static struct
{
  GoaProviderFeatures feature;
  const gchar *key;
} provider_features_info[] = {
  {
    .feature = GOA_PROVIDER_FEATURE_MAIL,
    .key = "MailEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_CALENDAR,
    .key = "CalendarEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_CONTACTS,
    .key = "ContactsEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_CHAT,
    .key = "ChatEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_DOCUMENTS,
    .key = "DocumentsEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_MUSIC,
    .key = "MusicEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_PHOTOS,
    .key = "PhotosEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_FILES,
    .key = "FilesEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_TICKETING,
    .key = "TicketingEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_READ_LATER,
    .key = "ReadLaterEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_PRINTERS,
    .key = "PrintersEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_MAPS,
    .key = "MapsEnabled"
  },
  {
    .feature = GOA_PROVIDER_FEATURE_INVALID,
    .key = NULL
  }
};

static void
get_all (GObject *source_object, GAsyncResult *res, gpointer user_data)
{
  GError *error;
  GList *providers = NULL;
  GList *l;
  GMainLoop *loop = (GMainLoop *) user_data;
  GKeyFile *key_file = NULL;
  gchar *key_file_data = NULL;

  error = NULL;
  if (!goa_provider_get_all_finish (&providers, res, &error))
    {
      g_warning ("Unable to get list of providers: %s", error->message);
      g_error_free (error);
      goto out;
    }

  key_file = g_key_file_new ();

  for (l = providers; l != NULL; l=l->next)
    {
      GoaProvider *provider = GOA_PROVIDER (l->data);
      GoaProviderFeatures features;
      const gchar *type;
      gchar *group;
      guint i;

      features = goa_provider_get_provider_features (provider);
      if (features == GOA_PROVIDER_FEATURE_INVALID)
        continue;

      type = goa_provider_get_provider_type (provider);
      group = g_strconcat ("Provider ", type, NULL);

      for (i = 0; provider_features_info[i].key != NULL; i++)
        {
          if ((features & provider_features_info[i].feature) != 0)
            {
              const gchar *key = provider_features_info[i].key;

              /* The IMAP/SMTP provider uses Enabled instead of
               * MailEnabled. We should probably fix it for consistency.
               */
              if (g_strcmp0 (type, "imap_smtp") == 0 && g_strcmp0 (key, "MailEnabled") == 0)
                key = "Enabled";

              g_key_file_set_boolean (key_file, group, key, TRUE);
            }
        }

      g_free (group);
    }

  error = NULL;
  key_file_data = g_key_file_to_data (key_file, NULL, &error);
  if (error != NULL)
    {
      g_warning ("Unable to serialize key file: %s", error->message);
      g_error_free (error);
      goto out;
    }

  g_print ("%s", key_file_data);

 out:
  g_clear_pointer (&key_file, (GDestroyNotify) g_key_file_unref);
  g_free (key_file_data);
  g_list_free_full (providers, g_object_unref);
  g_main_loop_quit (loop);
}

gint
main (void)
{
  GMainLoop *loop;

  setlocale (LC_ALL, "");

  /* Workaround https://bugzilla.gnome.org/show_bug.cgi?id=674885. */
  g_type_ensure (G_TYPE_DBUS_CONNECTION);

  loop = g_main_loop_new (NULL, FALSE);

  goa_provider_get_all (get_all, loop);
  g_main_loop_run (loop);

  g_main_loop_unref (loop);
  return 0;
}
