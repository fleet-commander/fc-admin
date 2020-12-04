#!/usr/bin/env python-wrapper.sh
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
import json
import logging
import os
import unittest

# GObject Introspection imports
import gi

gi.require_version("Json", "1.0")

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Json as gi_json

import fleet_commander_logger as FleetCommander

logger = logging.getLogger(os.path.basename(__file__))

# Get mainloop
ml = GLib.MainLoop()


# Test helpers
def mainloop_quit_callback(*args, **kwargs):
    logger.error("Timed out waiting for file update notification. Test probably failed")
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


class NMConnectionMock:
    def __init__(self, conn_type, settings, secrets):
        self.type = conn_type
        self.settings = settings
        self.secrets = secrets

    def to_dbus(self, flag):
        return self.settings

    def get_connection_type(self):
        return self.type

    def get_secrets(self, setting, cancellable):
        return self.secrets


class NMClientMock:
    def __init__(self):
        self.handler = None

    def connect(self, s, f):
        self.handler = f

    def emit_connection_added(self, conn):
        self.handler(self, conn)


# Pathching NM library
FleetCommander.NM.Client = NMClientMock
FleetCommander.NM.ConnectionSerializationFlags.ALL = 1

FleetCommander.NMLogger.NM_BUS = Gio.BusType.SESSION


class TestNMLogger(unittest.TestCase):
    def serialize_config_object(self, obj):
        if not isinstance(obj, dict):
            return None

        dict_top = GLib.VariantBuilder.new(GLib.VariantType("a{sa{sv}}"))
        for key_top in obj.keys():
            dict_sub = GLib.VariantDict.new(GLib.Variant("a{sv}", {}))
            if not isinstance(obj[key_top], dict):
                continue

            for key_sub in obj[key_top].keys():
                item = gi_json.gvariant_deserialize_data(
                    json.dumps(obj[key_top][key_sub]), -1, None
                )
                dict_sub.insert_value(key_sub, item)

            entry = GLib.VariantBuilder.new(GLib.VariantType("{sa{sv}}"))
            entry.add_value(GLib.Variant("s", key_top))
            entry.add_value(dict_sub.end())

            dict_top.add_value(entry.end())

        return dict_top.end()

    def setup_network_connection(self, conn_type, settings, secrets):
        connmgr = MockConnectionManager()
        nmlogger = FleetCommander.NMLogger(connmgr)
        settings_variant = self.serialize_config_object(settings)
        secrets_variant = self.serialize_config_object(secrets)
        conn = NMConnectionMock(conn_type, settings_variant, secrets_variant)

        # FIXME: BUG connection in NM module is not working
        # def check_bus_name(myconn):
        #     nmlogger.nmclient.emit_connection_added(myconn)
        #     ml.quit()

        def check_bus_name(myconn):
            nmlogger.submit_connection(myconn)
            ml.quit()

        # We wait for the logger to catch the bus name
        GLib.idle_add(check_bus_name, conn)

        GLib.timeout_add(3000, mainloop_quit_callback)
        ml.run()

        return connmgr

    def unmarshall_variant(self, data):
        return GLib.Variant.parse(None, data, None, None)

    def lookup_string(self, variant, path):
        return self.lookup_value(variant, path).get_string()

    def lookup_value(self, variant, path):
        sub = variant
        split = path.split(".")
        for i in split:
            sub = sub.lookup_value(i, None)
        return sub

    def test_01_vpn(self):
        connmgr = self.setup_network_connection(
            "vpn",
            {
                "vpn": {"user": "foo", "passwd": ""},
                "connection": {
                    "uuid": "connection_uuid",
                    "type": "vpn",
                    "id": "connection_id",
                },
            },
            {"vpn": {"passwd": "asd"}},
        )
        item = connmgr.pop()
        self.assertEqual(item[0], "org.freedesktop.NetworkManager")
        payload = json.loads(item[1])
        conf = self.unmarshall_variant(payload["data"])
        self.assertEqual(self.lookup_string(conf, "vpn.user"), "foo")
        self.assertEqual(self.lookup_string(conf, "vpn.passwd"), "asd")

        self.assertEqual(self.lookup_string(conf, "connection.uuid"), "connection_uuid")
        self.assertEqual(self.lookup_string(conf, "connection.type"), "vpn")
        self.assertEqual(self.lookup_string(conf, "connection.id"), "connection_id")

    def test_02_ethernet(self):
        connmgr = self.setup_network_connection(
            "802-3-ethernet",
            {
                "802-1x": {"user": "foo", "passwd": ""},
                "connection": {
                    "uuid": "connection_uuid",
                    "type": "802-3-ethernet",
                    "id": "connection_id",
                },
            },
            {"802-1x": {"passwd": "asd"}},
        )
        item = connmgr.pop()
        self.assertEqual(item[0], "org.freedesktop.NetworkManager")
        payload = json.loads(item[1])
        conf = self.unmarshall_variant(payload["data"])
        self.assertEqual(self.lookup_string(conf, "802-1x.user"), "foo")
        self.assertEqual(self.lookup_string(conf, "802-1x.passwd"), "asd")

        self.assertEqual(self.lookup_string(conf, "connection.uuid"), "connection_uuid")
        self.assertEqual(self.lookup_string(conf, "connection.type"), "802-3-ethernet")
        self.assertEqual(self.lookup_string(conf, "connection.id"), "connection_id")

    def test_03_wifi(self):
        connmgr = self.setup_network_connection(
            "802-11-wireless",
            {
                "802-11-wireless-security": {"user": "foo", "passwd": ""},
                "connection": {
                    "uuid": "connection_uuid",
                    "type": "802-11-wireless",
                    "id": "connection_id",
                },
            },
            {"802-11-wireless-security": {"passwd": "asd"}},
        )
        item = connmgr.pop()
        self.assertEqual(item[0], "org.freedesktop.NetworkManager")
        payload = json.loads(item[1])
        conf = self.unmarshall_variant(payload["data"])
        self.assertEqual(
            self.lookup_string(conf, "802-11-wireless-security.user"), "foo"
        )
        self.assertEqual(
            self.lookup_string(conf, "802-11-wireless-security.passwd"), "asd"
        )

        self.assertEqual(self.lookup_string(conf, "connection.uuid"), "connection_uuid")
        self.assertEqual(self.lookup_string(conf, "connection.type"), "802-11-wireless")
        self.assertEqual(self.lookup_string(conf, "connection.id"), "connection_id")

    def test_04_filters(self):
        secrets = {
            "802-11-wireless-security": {
                "username": "me",
                "leap-password": "somepassword",
            },
            "802-1x": {"username": "me", "password": "somepassword"},
            "vpn": {
                "data": {
                    "secrets": {
                        "username": "asd",
                        "password": "somepassword",
                        "Xauth password": "somepassword",
                    }
                }
            },
        }

        # VPN
        connmgr = self.setup_network_connection("vpn", {}, secrets)
        item = connmgr.pop()
        self.assertEqual(item[0], "org.freedesktop.NetworkManager")

        vpnout = json.loads(item[1])
        self.assertTrue(isinstance(vpnout, dict))
        vpnconf = self.unmarshall_variant(vpnout["data"])
        self.assertEqual(self.lookup_value(vpnconf, "vpn.data.secrets.password"), None)
        self.assertEqual(
            self.lookup_value(vpnconf, "vpn.data.secrets.Xauth password"), None
        )

        # Ethernet
        connmgr = self.setup_network_connection("802-3-ethernet", {}, secrets)
        item = connmgr.pop()

        self.assertEqual(item[0], "org.freedesktop.NetworkManager")

        ethout = json.loads(item[1])
        self.assertTrue(isinstance(ethout, dict))
        ethconf = self.unmarshall_variant(ethout["data"])
        self.assertEqual(self.lookup_value(ethconf, "802-1x.password"), None)

        # Wifi
        connmgr = self.setup_network_connection("802-11-wireless", {}, secrets)
        item = connmgr.pop()

        self.assertEqual(item[0], "org.freedesktop.NetworkManager")
        wifiout = json.loads(item[1])
        self.assertTrue(isinstance(wifiout, dict))
        wificonf = self.unmarshall_variant(wifiout["data"])
        self.assertEqual(self.lookup_value(wificonf, "802-1x.password"), None)
        self.assertEqual(
            self.lookup_value(wificonf, "802-11-wireless-security.leap-password"), None
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
