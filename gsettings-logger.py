from gi.repository import GLib
from gi.repository import Gio

log = []
all_settings = {}
schema_source = Gio.SettingsSchemaSource.get_default()

# List all schemas
noreloc, reloc = schema_source.list_schemas(True)
for sch_id in noreloc:
  all_settings[sch_id] = Gio.Settings(sch_id)

### We cannot support non relocatables Schemas for the time being ###
#for sch_id in reloc:
#  schema = schema_source.lookup (sch_id, True)
#  all_settings[sch_id] = Gio.Settings.new_with_path(sch_id, schema.get_path ())

# Listen for any changes within those schemas
def changed_callback (gsettings, key):
  print (gsettings.get_property("path"), key, gsettings.get_user_value (key))

for id in all_settings:
  all_settings[id].connect("changed", changed_callback)

ml = GLib.MainLoop (None)
ml.run()
