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
import os
import shutil
import tempfile
import subprocess
import time
import unittest
import json
import logging

# Fleet commander imports
from fleetcommander import sshcontroller

# Tests imports
from test_fcdbus_service import MockLibVirtController
from fcdbusclient import FleetCommanderDbusClient

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)


class TestDbusService(unittest.TestCase):

    maxDiff = None

    TEMPLATE_UUID = "e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81"
    SESSION_UUID = "fefb45d9-5a81-3392-b7bc-e2e37c2d"

    DUMMY_PROFILE_CN = "foo"
    DUMMY_PROFILE_PAYLOAD = {
        "cn": DUMMY_PROFILE_CN,
        "name": "bar",
        "description": "baz",
        "priority": 51,
        "settings": {},
        "users": "admin,guest",
        "groups": "editors",
        "hosts": "client1,",
        "hostgroups": "",
    }

    DUMMY_PROFILE_DATA = {
        "cn": "foo",
        "name": "bar",
        "description": "baz",
        "priority": 51,
        "settings": {},
        "users": [
            "admin",
            "guest",
        ],
        "groups": [
            "editors",
        ],
        "hosts": [
            "client1",
        ],
        "hostgroups": [],
    }

    MAX_DBUS_CHECKS = 10

    DUMMY_GOA_PROVIDERS_DATA = {
        "provider": {
            "name": "Provider",
            "services": {
                "MailEnabled": {"enabled": True, "name": "Mail"},
                "DocumentsEnabled": {"enabled": True, "name": "Documents"},
            },
        },
        "pizza_provider": {
            "name": "My Pizza Provider",
            "services": {
                "HotdogEnabled": {"enabled": False, "name": "Hotdog"},
                "PizzaEnabled": {"enabled": True, "name": "Pizza"},
                "PepperoniEnabled": {"enabled": True, "name": "Pepperoni"},
            },
        },
        "special_provider": {
            "name": "Special Provider",
            "services": {
                "Enabled": {"enabled": True, "name": "Enabled"},
            },
        },
    }

    def setUp(self):
        self.test_directory = tempfile.mkdtemp()

        self.args = {
            "database_path": os.path.join(self.test_directory, "database.db"),
            "tmp_session_destroy_timeout": 60,
        }

        # Open service
        self.service = subprocess.Popen(
            [
                os.environ["PYTHON"],
                os.path.join(os.environ["TOPSRCDIR"], "tests/test_fcdbus_service.py"),
                self.test_directory,
            ]
        )

        checks = 0
        while True:
            try:
                self.c = FleetCommanderDbusClient()
                self.c.get_public_key()
                break
            except Exception:
                checks += 1
                if checks < self.MAX_DBUS_CHECKS:
                    time.sleep(0.1)
                else:
                    raise Exception(
                        "Test error: " + "DBUS Service is taking too much to start"
                    )

        self.ssh = sshcontroller.SSHController()
        self.known_hosts_file = os.path.join(self.test_directory, "known_hosts")

    def tearDown(self):
        # Kill service
        self.service.kill()
        shutil.rmtree(self.test_directory)

    def get_data_from_file(self, path):
        """
        Reads JSON file contents
        """
        with open(path, "r") as fd:
            data = fd.read()
            fd.close()
        return json.loads(data)

    def get_profile_data(self, profile_name):
        filepath = os.path.join(self.test_directory, "directorymock-data.json")
        data = self.get_data_from_file(filepath)
        if profile_name in data["profiles"]:
            return data["profiles"][profile_name]
        return None

    def configure_hypervisor(self):
        # Configure hypervisor
        self.c.set_hypervisor_config(
            {
                "host": "myhost",
                "username": "valid_user",
                "mode": "session",
                "keys": "myhost ssh-rsa KEY",
            }
        )

    def test_00_get_initial_values(self):
        logging.debug("TEST 00")
        state = {
            "debuglevel": "debug",
            "defaults": {
                "profilepriority": 50,
            },
            "realm": "fc.directory",
            "server_type": "active-directory",
        }
        self.assertEqual(json.loads(self.c.get_initial_values()), state)

    def test_01_do_domain_connection(self):
        logging.debug("TEST 01")
        self.assertEqual(json.loads(self.c.do_domain_connection()), {"status": True})

    def test_02_get_public_key(self):
        logging.debug("TEST 02")
        self.assertEqual(self.c.get_public_key(), "PUBLIC_KEY")

    def test_03_get_hypervisor_config(self):
        logging.debug("TEST 03")
        self.assertEqual(
            self.c.get_hypervisor_config(),
            {
                "pubkey": "PUBLIC_KEY",
                "host": "",
                "username": "",
                "mode": "system",
                "needcfg": True,
            },
        )

    def test_04_check_hypervisor_config(self):
        logging.debug("TEST 04")
        data = {
            "host": "localhost",
            "username": "valid_user",
            "mode": "session",
        }

        # Set invalid host data
        idata = data.copy()
        idata["host"] = "invalid_host"
        resp = self.c.check_hypervisor_config(idata)
        self.assertFalse(resp["status"])
        self.assertEqual(resp["errors"], {"host": "Invalid hostname specified"})

        # Set invalid username data
        idata = data.copy()
        idata["username"] = "invalid#username"
        resp = self.c.check_hypervisor_config(idata)
        self.assertFalse(resp["status"])
        self.assertEqual(resp["errors"], {"username": "Invalid username specified"})

        # Set invalid session data
        idata = data.copy()
        idata["mode"] = "invalidmode"
        resp = self.c.check_hypervisor_config(idata)
        self.assertFalse(resp["status"])
        self.assertEqual(resp["errors"], {"mode": "Invalid session type"})

    def test_05_set_hypervisor_config(self):
        logging.debug("TEST 05")
        data = {
            "host": "localhost",
            "username": "valid_user",
            "mode": "session",
            "adminhost": "",
        }

        dataresp = data.copy()
        dataresp["pubkey"] = "PUBLIC_KEY"

        # Set data
        resp = self.c.set_hypervisor_config(data)
        self.assertTrue(resp["status"])

        # Retrieve configuration and compare
        self.assertEqual(self.c.get_hypervisor_config(), dataresp)

    def test_06_check_known_host(self):
        logging.debug("TEST 06")
        # Check not known host
        resp = self.c.check_known_host("localhost")
        self.assertFalse(resp["status"])
        self.assertEqual(resp["fprint"], "2048 SHA256:HASH localhost (RSA)\n")
        self.assertEqual(resp["keys"], "localhost ssh-rsa KEY\n")

        # Add host to known hosts
        self.ssh.add_keys_to_known_hosts(
            self.known_hosts_file, "localhost ssh-rsa KEY\n"
        )

        # Check already known host
        resp = self.c.check_known_host("localhost")
        self.assertTrue(resp["status"])

    def test_07_add_known_host(self):
        logging.debug("TEST 07")
        # Check not known host
        resp = self.c.check_known_host("localhost")
        self.assertFalse(resp["status"])

        # Add host to known hosts
        self.c.add_known_host("localhost")

        # Check already known host
        resp = self.c.check_known_host("localhost")
        self.assertTrue(resp["status"])

    def test_08_install_public_key(self):
        logging.debug("TEST 08")
        # Test install with bad credentials
        resp = self.c.install_pubkey(
            "localhost",
            "username",
            "badpassword",
        )
        self.assertFalse(resp["status"])

        # Test install with correct credentials
        resp = self.c.install_pubkey(
            "localhost",
            "username",
            "password",
        )
        self.assertTrue(resp["status"])

    def test_09_save_profile(self):
        logging.debug("TEST 09")
        # Create a new profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        self.assertTrue(resp["status"])
        data = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertEqual(data, self.DUMMY_PROFILE_DATA)

    def test_10_delete_profile(self):
        logging.debug("TEST 10")
        # Delete unexistent profile
        resp = self.c.delete_profile("fakeuid")
        self.assertTrue(resp["status"])
        # Delete existent profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        data = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertTrue(data is not None)
        self.assertEqual(data, self.DUMMY_PROFILE_DATA)
        resp = self.c.delete_profile(self.DUMMY_PROFILE_CN)
        self.assertTrue(resp["status"])
        data = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertTrue(data is None)

    def test_11_list_domains(self):
        logging.debug("TEST 11")
        # Try to get domains without configuring hypervisor
        resp = self.c.list_domains()
        self.assertFalse(resp["status"])
        self.assertEqual(resp["error"], "Error retrieving domains")

        # Configure hypervisor
        self.configure_hypervisor()

        # Get domains
        resp = self.c.list_domains()
        self.assertTrue(resp["status"])
        self.assertEqual(resp["domains"], MockLibVirtController.DOMAINS_LIST)

    def test_12_session_start(self):
        logging.debug("TEST 12")
        # Configure hypervisor
        self.configure_hypervisor()
        # Start session
        resp = self.c.session_start(self.TEMPLATE_UUID)
        self.assertTrue(resp["status"])
        self.assertEqual(resp["port"], 0)
        # Try to start another session
        resp = self.c.session_start(self.TEMPLATE_UUID)
        self.assertFalse(resp["status"])
        self.assertEqual(resp["error"], "Session already started")

    def test_13_session_stop(self):
        logging.debug("TEST 13")
        # Configure hypervisor
        self.configure_hypervisor()
        # Stop without previous session start
        resp = self.c.session_stop()
        self.assertFalse(resp["status"])
        self.assertEqual(resp["error"], "There was no session started")
        # Stop previous started session
        self.c.session_start(self.TEMPLATE_UUID)
        resp = self.c.session_stop()
        self.assertTrue(resp["status"])
        # Stop again
        resp = self.c.session_stop()
        self.assertFalse(resp["status"])
        self.assertEqual(resp["error"], "There was no session started")

    def test_14_empty_session_save(self):
        logging.debug("TEST 14")
        # Create a profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        # Configure hypervisor
        self.configure_hypervisor()
        # Start a session
        self.c.session_start(self.TEMPLATE_UUID)
        # Save empty session
        resp = self.c.session_save(self.DUMMY_PROFILE_CN, {})
        self.assertTrue(resp["status"])
        # Check profile is unmodified?
        data = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertTrue(data is not None)
        self.assertEqual(data["settings"], {})

    def test_15_session_save(self):
        logging.debug("TEST 15")
        # Create a profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        # Configure hypervisor
        self.configure_hypervisor()
        # Start a session
        self.c.session_start(self.TEMPLATE_UUID)
        data = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertTrue(data is not None)
        gsettings = data["settings"]
        self.assertEqual(gsettings, {})

        # Save session
        settings = {
            "org.gnome.gsettings": [
                {"value": True, "key": "/foo/bar", "signature": "b"}
            ]
        }
        resp = self.c.session_save(self.DUMMY_PROFILE_CN, settings)
        self.assertTrue(resp["status"])
        profdata = self.get_profile_data(self.DUMMY_PROFILE_CN)
        self.assertTrue(profdata is not None)
        gsettings = profdata["settings"]["org.gnome.gsettings"]
        self.assertEqual(len(gsettings), 1)
        self.assertEqual(gsettings[0]["value"], True)
        self.assertEqual(gsettings[0]["signature"], "b")
        self.assertEqual(gsettings[0]["key"], "/foo/bar")

    def test_16_get_profiles(self):
        logging.debug("TEST 16")
        # Create a profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        # Get profiles data
        resp = self.c.get_profiles()
        # Check profiles data
        self.assertTrue(resp["status"])
        self.assertEqual(
            resp["data"],
            [
                [
                    self.DUMMY_PROFILE_CN,
                    self.DUMMY_PROFILE_PAYLOAD["name"],
                    self.DUMMY_PROFILE_PAYLOAD["description"],
                ]
            ],
        )

    def test_17_get_profile(self):
        logging.debug("TEST 17")
        # Create a profile
        resp = self.c.save_profile(self.DUMMY_PROFILE_PAYLOAD)
        # Get profile data
        resp = self.c.get_profile(self.DUMMY_PROFILE_CN)
        # Check profile data
        self.assertTrue(resp["status"])
        profile = self.DUMMY_PROFILE_DATA.copy()
        self.assertEqual(resp["data"], profile)

    def test_18_get_goa_providers(self):
        logging.debug("TEST 18")
        resp = self.c.get_goa_providers()
        self.assertTrue(resp["status"])
        self.assertEqual(resp["providers"], self.DUMMY_GOA_PROVIDERS_DATA)

    def test_19_is_session_active(self):
        logging.debug("TEST 19")
        # Configure hypervisor
        self.configure_hypervisor()

        # Check current session active without starting any
        resp = self.c.is_session_active()
        self.assertFalse(resp)

        # Check current session active after started current session
        self.c.session_start(self.TEMPLATE_UUID)
        resp = self.c.is_session_active()
        self.assertTrue(resp)

        # Check non existent session by its uuid
        resp = self.c.is_session_active("unknown")
        self.assertFalse(resp)

        # Check existent session by its uuid
        resp = self.c.is_session_active("")
        self.assertTrue(resp)


if __name__ == "__main__":
    unittest.main()
