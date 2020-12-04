# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

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
# from __future__ import absolute_import
# import os
# import sys
import time
import json
import logging

import dbus

# PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
# sys.path.append(PYTHONPATH)

logger = logging.getLogger(__name__)

DBUS_BUS_NAME = "org.freedesktop.FleetCommanderTest"
DBUS_OBJECT_PATH = "/org/freedesktop/FleetCommanderTest"
DBUS_INTERFACE_NAME = "org.freedesktop.FleetCommander"
DBUS_TESTING_INTERFACE_NAME = "org.freedesktop.FleetCommanderTest"


class FleetCommanderDbusClient:

    """
    Fleet commander dbus client
    """

    DEFAULT_BUS = dbus.SessionBus
    CONNECTION_TIMEOUT = 1

    def __init__(self, bus=None):
        """
        Class initialization
        """
        if bus is None:
            bus = self.DEFAULT_BUS()
        self.bus = bus

        t = time.time()
        while time.time() - t < self.CONNECTION_TIMEOUT:
            try:
                self.obj = self.bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
                self.iface = dbus.Interface(
                    self.obj, dbus_interface=DBUS_INTERFACE_NAME
                )
                return
            except Exception:
                pass
        raise Exception("Timed out trying to connect to fleet commander dbus service")

    def get_initial_values(self):
        return self.iface.GetInitialValues()

    def do_domain_connection(self):
        return self.iface.DoDomainConnection()

    def heartbeat(self):
        return self.iface.HeartBeat()

    def check_needs_configuration(self):
        return self.iface.CheckNeedsConfiguration()

    def get_public_key(self):
        return self.iface.GetPublicKey()

    def check_hypervisor_config(self, data):
        return json.loads(self.iface.CheckHypervisorConfig(json.dumps(data)))

    def get_hypervisor_config(self):
        return json.loads(self.iface.GetHypervisorConfig())

    def set_hypervisor_config(self, data):
        return json.loads(self.iface.SetHypervisorConfig(json.dumps(data)))

    def check_known_host(self, host):
        return json.loads(self.iface.CheckKnownHost(host))

    def add_known_host(self, host):
        return json.loads(self.iface.AddKnownHost(host))

    def install_pubkey(self, host, user, passwd):
        return json.loads(self.iface.InstallPubkey(host, user, passwd))

    def get_global_policy(self):
        return json.loads(self.iface.GetGlobalPolicy())

    def set_global_policy(self, policy):
        return json.loads(self.iface.SetGlobalPolicy(policy))

    def save_profile(self, profiledata):
        return json.loads(self.iface.SaveProfile(json.dumps(profiledata)))

    def get_profiles(self):
        return json.loads(self.iface.GetProfiles())

    def get_profile(self, uid):
        return json.loads(self.iface.GetProfile(uid))

    def delete_profile(self, uid):
        return json.loads(self.iface.DeleteProfile(uid))

    def list_domains(self):
        return json.loads(self.iface.ListDomains())

    def session_start(self, domain_uuid):
        return json.loads(self.iface.SessionStart(domain_uuid))

    def session_stop(self):
        return json.loads(self.iface.SessionStop())

    def session_save(self, uid, data):
        return json.loads(self.iface.SessionSave(uid, json.dumps(data)))

    def is_session_active(self, uuid=""):
        return self.iface.IsSessionActive(uuid)

    def get_change_listener_port(self):
        return self.iface.GetChangeListenerPort()

    def get_goa_providers(self):
        return json.loads(self.iface.GetGOAProviders())

    def quit(self):
        return self.iface.Quit()
