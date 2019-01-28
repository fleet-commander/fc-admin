from __future__ import absolute_import
import dbus.service
import dbusmock
import dbus.mainloop.glib
from gi.repository import GLib

ml = GLib.MainLoop()

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

bus = dbusmock.testcase.DBusTestCase.get_dbus()

bus.add_signal_receiver(
    ml.quit,
    signal_name='Disconnected',
    path='/org/freedesktop/DBus/Local',
    dbus_interface='org.freedesktop.DBus.Local')

realmd_bus = dbus.service.BusName(
    "org.freedesktop.realmd",
    bus,
    allow_replacement=True,
    replace_existing=True,
    do_not_queue=True)

# Provider
provider = dbusmock.mockobject.DBusMockObject(
    realmd_bus,
    "/org/freedesktop/realmd/Sssd",
    "org.freedesktop.realmd.Provider",
    {})

provider.AddProperty("Realms", ['/org/freedesktop/realmd/Sssd/fc_ipa_X'])

# Realm
realm = dbusmock.mockobject.DBusMockObject(
    realmd_bus,
    "/org/freedesktop/realmd/Sssd/fc_ipa_X",
    "org.freedesktop.realmd.Realm",
    {})

realm.AddProperty("Name", 'fc.ipa')
realm.AddProperty(
    "Details", [
        ('server-software', 'ipa'), ('client-software', 'sssd')])

ml.run()
