from __future__ import absolute_import

import logging

import dbus.service
import dbusmock
import dbus.mainloop.glib
from gi.repository import GLib

logger = logging.getLogger(os.path.basename(__file__))

ml = GLib.MainLoop()

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

bus = dbusmock.testcase.DBusTestCase.get_dbus()

bus.add_signal_receiver(
    ml.quit,
    signal_name="Disconnected",
    path="/org/freedesktop/DBus/Local",
    dbus_interface="org.freedesktop.DBus.Local",
)

realmd_bus = dbus.service.BusName(
    "org.freedesktop.realmd",
    bus,
    allow_replacement=True,
    replace_existing=True,
    do_not_queue=True,
)

# Provider
provider = dbusmock.mockobject.DBusMockObject(
    realmd_bus,
    "/org/freedesktop/realmd/Sssd",
    "org.freedesktop.realmd.Provider",
    {"Realms": ["/org/freedesktop/realmd/Sssd/fc_ipa_X"]},
)

# Realm
realm = dbusmock.mockobject.DBusMockObject(
    realmd_bus,
    "/org/freedesktop/realmd/Sssd/fc_ipa_X",
    "org.freedesktop.realmd.Realm",
    {
        "Name": "fc.directory",
        "Details": [
            ("server-software", "active-directory"),
            ("client-software", "sssd"),
        ],
    },
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Configured and running realmd dbus mock")
    ml.run()
    logging.debug("Quitting realmd dbus mock")
