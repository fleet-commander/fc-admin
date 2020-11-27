# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the licence, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>

# Python imports
from __future__ import absolute_import
import sys
import os
import json
import logging
import unittest

import dbus

# GObject Introspection imports
from gi.repository import GLib
from gi.repository import Gio

PYTHONPATH = os.path.join(os.environ["TOPSRCDIR"], "logger")
sys.path.append(PYTHONPATH)

import fleet_commander_logger as FleetCommander

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)

# Get mainloop
ml = GLib.MainLoop()


# Test helpers
def mainloop_quit_callback(*args, **kwargs):
    logging.error("Timed out waiting for DBus call. Test probably failed")
    ml.quit()


class MockConnectionManager:
    """
    Connection Manager mock class
    """

    def __init__(self):
        self.log = []

    def submit_change(self, namespace, data):
        self.log.append([namespace, data])

    def pop(self):
        return self.log.pop(0)

    def finish_changes(self):
        ml.quit()


class TestScreenSaverInhibitor(unittest.TestCase):
    def test_01_inhibitor_init(self):
        inhibitor = FleetCommander.ScreenSaverInhibitor()
        self.assertTrue("org.freedesktop.ScreenSaver" in inhibitor.screensavers)
        self.assertTrue(
            inhibitor.screensavers["org.freedesktop.ScreenSaver"]["cookie"] == 9191
        )

    def test_02_inhibitor_unknown_screensaver(self):
        inhibitor = FleetCommander.ScreenSaverInhibitor()
        inhibitor.inhibit("org.unknown.FakeScreenSaver")
        self.assertFalse("org.unknown.FakeScreenSaver" in inhibitor.screensavers)

    def test_03_inhibitor_uninhibit(self):
        inhibitor = FleetCommander.ScreenSaverInhibitor()
        self.assertTrue("org.freedesktop.ScreenSaver" in inhibitor.screensavers)
        self.assertTrue(
            inhibitor.screensavers["org.freedesktop.ScreenSaver"]["cookie"] == 9191
        )
        inhibitor.uninhibit()
        self.assertTrue(inhibitor.screensavers == {})


class TestDconfLogger(unittest.TestCase):
    def setup_dbus_call(self, method, args, glog):
        proxy = dbus.SessionBus().get_object(glog.BUS_NAME, glog.OBJECT_PATH)

        iface = dbus.Interface(proxy, dbus_interface=glog.INTERFACE_NAME)

        # We wait for the logger to catch the bus name
        def check_dbus_name():
            if glog.dconf_subscription_id != 0:
                logging.debug(
                    "Signal registered. Calling '%s' dbus method. Args: %s",
                    method,
                    args,
                )
                getattr(iface, method)(*args)
                return False
            return True

        GLib.idle_add(check_dbus_name)

        GLib.timeout_add(3000, mainloop_quit_callback)

        ml.run()

    def unsubscribe_signal(self, glog):
        Gio.bus_get_sync(Gio.BusType.SESSION, None).signal_unsubscribe(
            glog.dconf_subscription_id
        )

    def test_01_write_key_for_known_schema(self):
        mgr = MockConnectionManager()
        glog = FleetCommander.GSettingsLogger(mgr)
        glog._testing_loop = ml

        args = [[]]  # GLib.Variant.new("(ay)", [[]])
        self.setup_dbus_call("Change", args, glog)

        change = mgr.pop()
        self.assertTrue(change is not None)
        self.assertEqual(len(change), 2)

        self.assertEqual(change[0], "org.gnome.gsettings")

        # Normalize the json object using the same parser
        self.assertEqual(
            json.dumps(
                {
                    "key": "/test/test",
                    "schema": "fleet-commander-test",
                    "value": "true",
                    "signature": "b",
                },
                sort_keys=True,
            ),
            json.dumps(json.loads(change[1]), sort_keys=True),
        )

        # Unsubscribe logger dbus signal
        self.unsubscribe_signal(glog)

    def test_02_write_key_for_unknown_schema(self):
        mgr = MockConnectionManager()
        glog = FleetCommander.GSettingsLogger(mgr)
        glog._testing_loop = ml

        self.setup_dbus_call("ChangeCommon", [], glog)

        self.assertEqual(len(mgr.log), 0)

        # Unsubscribe logger dbus signal
        self.unsubscribe_signal(glog)

    def test_03_write_key_for_guessable_schema(self):
        mgr = MockConnectionManager()
        glog = FleetCommander.GSettingsLogger(mgr)
        glog._testing_loop = ml

        self.setup_dbus_call("ChangeUnique", [], glog)

        change = mgr.pop()

        self.assertEqual(change[0], "org.gnome.gsettings")
        self.assertEqual(
            json.dumps(
                {
                    "key": "/reloc/foo/fc-unique",
                    "schema": "fleet-commander-reloc1",
                    "value": "true",
                    "signature": "b",
                },
                sort_keys=True,
            ),
            json.dumps(json.loads(change[1]), sort_keys=True),
        )

        # Unsubscribe logger dbus signal
        self.unsubscribe_signal(glog)

    def test_04_guess_schema_cached_path(self):
        mgr = MockConnectionManager()
        glog = FleetCommander.GSettingsLogger(mgr)
        glog._testing_loop = ml

        self.setup_dbus_call("ChangeCommon", [], glog)
        self.setup_dbus_call("ChangeUnique", [], glog)
        mgr.pop()
        self.setup_dbus_call("ChangeCommon", [], glog)

        change = mgr.pop()
        self.assertEqual(change[0], "org.gnome.gsettings")
        self.assertEqual(
            json.dumps(
                {
                    "key": "/reloc/foo/fc-common",
                    "schema": "fleet-commander-reloc1",
                    "value": "true",
                    "signature": "b",
                },
                sort_keys=True,
            ),
            json.dumps(json.loads(change[1]), sort_keys=True),
        )

        # Unsubscribe logger dbus signal
        self.unsubscribe_signal(glog)

    def test_05_libreoffice_write_key(self):
        mgr = MockConnectionManager()
        glog = FleetCommander.GSettingsLogger(mgr)
        glog._testing_loop = ml

        self.setup_dbus_call("ChangeLibreOffice", [], glog)

        change = mgr.pop()

        self.assertTrue(change is not None)
        self.assertTrue(len(change) == 2)

        self.assertEqual(change[0], "org.libreoffice.registry")

        # We normalize the json object using the same parser
        self.assertEqual(
            json.dumps(
                {
                    "key": "/org/libreoffice/registry/somepath/somekey",
                    "value": "123",
                    "signature": "i",
                },
                sort_keys=True,
            ),
            json.dumps(json.loads(change[1]), sort_keys=True),
        )

        # Unsubscribe logger dbus signal
        self.unsubscribe_signal(glog)

    def test_06_libreoffice_create_dconfwrite(self):
        home = GLib.dir_make_tmp("fcmdr-XXXXXX")

        mgr = MockConnectionManager()
        FleetCommander.GSettingsLogger(mgr, home)

        self.assertTrue(
            os.path.exists(os.path.join(home, ".config/libreoffice/dconfwrite"))
        )


if __name__ == "__main__":
    unittest.main()
