from __future__ import absolute_import

import logging

import dbus.service
import dbusmock
import dbus.mainloop.glib
from gi.repository import GLib

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)

ml = GLib.MainLoop()

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

bus = dbusmock.testcase.DBusTestCase.get_dbus()

bus.add_signal_receiver(
    ml.quit,
    signal_name="Disconnected",
    path="/org/freedesktop/DBus/Local",
    dbus_interface="org.freedesktop.DBus.Local",
)

nm_bus = dbus.service.BusName(
    "org.freedesktop.NetworkManager",
    bus,
    allow_replacement=True,
    replace_existing=True,
    do_not_queue=True,
)

logging.debug("Configured and running NetworkManager dbus mock")

ml.run()

logging.debug("Quitting NetworkManager dbus mock")
