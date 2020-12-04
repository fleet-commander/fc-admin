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
from __future__ import absolute_import

from collections import namedtuple

import os
import sys
import logging

from gi.repository import Gio

# Fleet commander imports
from fleetcommander import libvirtcontroller
from fleetcommander import sshcontroller
from fleetcommander import fcdbus

# Mock directory system
from tests import directorymock

logger = logging.getLogger(os.path.basename(__file__))

fcdbus.fcfreeipa.FreeIPAConnector = directorymock.DirectoryConnector
fcdbus.fcad.ADConnector = directorymock.DirectoryConnector

# Change bus names
fcdbus.DBUS_BUS_NAME = "org.freedesktop.FleetCommanderTest"
fcdbus.DBUS_OBJECT_PATH = "/org/freedesktop/FleetCommanderTest"


# Mock libvirt controller
def controller(viewer_type, data_path, username, hostname, mode):
    return MockLibVirtController(data_path, username, hostname, mode)


fcdbus.libvirtcontroller.controller = controller


class MockLibVirtController(libvirtcontroller.LibVirtTunnelSpice):

    TEMPLATE_UUID = "e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81"
    SESSION_UUID = "fefb45d9-5a81-3392-b7bc-e2e37c2d"

    DOMAINS_LIST = [
        {
            "uuid": TEMPLATE_UUID,
            "name": "fedora-unkno",
            "active": False,
            "temporary": False,
        }
    ]

    def __init__(self, data_path, username, hostname, mode):

        self.data_dir = os.path.abspath(data_path)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.public_key_file = os.path.join(self.data_dir, "id_rsa.pub")

        with open(self.public_key_file, "w") as fd:
            fd.write("PUBLIC_KEY")

        self.session_params = namedtuple(
            "session_params",
            [
                "domain",
                "details",
            ],
        )

    def list_domains(self):
        return self.DOMAINS_LIST

    def session_start(self, identifier, debug_logger=False):
        """Return abstract session cookie."""
        self.DOMAINS_LIST.append(
            {
                "uuid": self.SESSION_UUID,
                "name": "fc-",
                "active": True,
                "temporary": True,
            }
        )
        details = {
            "host": "localhost",
            "viewer": "spice_html5",
            "ticket": "spice_ticket",
        }

        return self.session_params(
            domain=self.SESSION_UUID,
            details=details,
        )

    def session_stop(self, identifier):
        for d in self.DOMAINS_LIST:
            if d["uuid"] == identifier:
                self.DOMAINS_LIST.remove(d)


class TestFleetCommanderDbusService(fcdbus.FleetCommanderDbusService):
    def __init__(self, test_directory):

        args = {
            "log_level": "debug",
            "log_format": "\n[%(levelname)s] %(asctime)-15s %(message)s",
            "debug_logger": False,
            "data_dir": test_directory,
            "tmp_session_destroy_timeout": 60,
            "auto_quit_timeout": 60,
            "default_profile_priority": 50,
            # Force state directory
            "state_dir": test_directory,
        }

        directorymock.DirectoryConnector.data = directorymock.DirectoryData(
            test_directory
        )

        self.REALMD_BUS = Gio.BusType.SESSION

        super().__init__(args)

        self.known_hosts_file = os.path.join(test_directory, "known_hosts")

        self.GOA_PROVIDERS_FILE = os.path.join(
            os.environ["TOPSRCDIR"], "tests/data/fc_goa_providers_test.ini"
        )

        self.ssh.install_pubkey = self.ssh_install_pubkey_mock

    def ssh_install_pubkey_mock(self, pubkey, user, password, host, port):
        """
        Just mock ssh command execution
        """
        if password != "password":
            raise sshcontroller.SSHControllerException("Invalid credentials")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    TestFleetCommanderDbusService(sys.argv[1]).run()
