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
    signal_name="Disconnected",
    path="/org/freedesktop/DBus/Local",
    dbus_interface="org.freedesktop.DBus.Local",
)


fdo_bus = dbus.service.BusName(
    "org.freedesktop.ScreenSaver",
    bus,
    allow_replacement=True,
    replace_existing=True,
    do_not_queue=True,
)

screensaver = dbusmock.mockobject.DBusMockObject(
    fdo_bus, "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver", {}
)
screensaver.AddMethods(
    "org.freedesktop.ScreenSaver",
    [
        ("Inhibit", "ss", "u", "ret = 9191"),
        ("UnInhibit", "u", "", ""),
    ],
)

dconf_bus = dbus.service.BusName(
    "ca.desrt.dconf",
    bus,
    allow_replacement=True,
    replace_existing=True,
    do_not_queue=True,
)

dconf = dbusmock.mockobject.DBusMockObject(
    dconf_bus, "/ca/desrt/dconf/Writer/user", "ca.desrt.dconf.Writer", {}
)
dconf.AddMethod(
    "ca.desrt.dconf.Writer",
    "Change",
    "ay",
    "s",
    'self.EmitSignal("ca.desrt.dconf.Writer", "Notify", "sass", ["/test/", ["test",], "tag"]);ret = "tag"',
)
dconf.AddMethod(
    "ca.desrt.dconf.Writer",
    "ChangeCommon",
    "",
    "",
    'self.EmitSignal("ca.desrt.dconf.Writer", "Notify", "sass", ["/reloc/foo/", ["fc-common",], "tag"])',
)
dconf.AddMethod(
    "ca.desrt.dconf.Writer",
    "ChangeUnique",
    "",
    "",
    'self.EmitSignal("ca.desrt.dconf.Writer", "Notify", "sass", ["/reloc/foo/", ["fc-unique",], "tag"])',
)
dconf.AddMethod(
    "ca.desrt.dconf.Writer",
    "ChangeUniqueAndCommon",
    "",
    "",
    'self.EmitSignal("ca.desrt.dconf.Writer", "Notify", "sass", ["/reloc/foo/", ["fc-unique","fc-common"], "tag"])',
)
dconf.AddMethod(
    "ca.desrt.dconf.Writer",
    "ChangeLibreOffice",
    "",
    "",
    'self.EmitSignal("ca.desrt.dconf.Writer", "Notify", "sass", ["/org/libreoffice/registry/somepath/", ["somekey",], "tag"])',
)

dbusmock.mockobject.objects["/ScreenSaver"] = screensaver
ml.run()
