#!/usr/bin/env  python-wrapper.sh
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

from __future__ import absolute_import
import os
import sys
import tempfile
import shutil
import unittest

sys.path.append(os.path.join(os.environ["TOPSRCDIR"], "admin"))

from fleetcommander import sshcontroller
from tests import (
    SSH_TUNNEL_OPEN_PARMS,
    SSH_TUNNEL_CLOSE_PARMS,
    SSH_REMOTE_COMMAND_PARMS,
)


class TestSSHController(unittest.TestCase):

    SSH_KEYGEN_PARMS = "-b 2048 -t rsa -f %s -q -N\n"
    SSH_KEYSCAN_PARMS = "-p %s %s\n"
    SSH_KEYSCAN_OUTPUT = "%s ssh-rsa KEY\n"
    SSH_KEYGEN_FINGERPRINT_OUTPUT = "2048 SHA256:HASH localhost (RSA)\n"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Python 3 compatibility
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp
        self.maxDiff = None

    def setUp(self):
        self.test_directory = tempfile.mkdtemp(prefix="fc-ssh-test")

        # Prepare paths for command output files
        self.ssh_keyscan_parms_file = os.path.join(
            self.test_directory, "ssh-keyscan-parms"
        )
        self.ssh_keygen_parms_file = os.path.join(
            self.test_directory, "ssh-keygen-parms"
        )
        self.ssh_parms_file = os.path.join(self.test_directory, "ssh-parms")
        self.known_hosts_file = os.path.join(self.test_directory, "known_hosts")
        self.private_key_file = os.path.join(self.test_directory, "id_rsa")
        self.public_key_file = os.path.join(self.test_directory, "id_rsa.pub")

        # Set environment for commands execution
        os.environ["FC_TEST_DIRECTORY"] = self.test_directory

    def tearDown(self):
        # Remove test directory
        shutil.rmtree(self.test_directory)

    def test_00_ssh_keypair_generation(self):
        # Generate key files
        ssh = sshcontroller.SSHController()
        ssh.generate_ssh_keypair(self.private_key_file)
        # Check parameters
        self.assertTrue(os.path.exists(self.ssh_keygen_parms_file))
        with open(self.ssh_keygen_parms_file, "r") as fd:
            parms = fd.read()
            fd.close()

        self.assertEqual(parms, self.SSH_KEYGEN_PARMS % self.private_key_file)

    def test_01_scan_host_keys(self):
        # Execute command
        ssh = sshcontroller.SSHController()
        hostname = "localhost"
        port = "2022"
        keys = ssh.scan_host_keys(hostname, port)
        # Check keys data
        self.assertEqual(keys, self.SSH_KEYSCAN_OUTPUT % hostname)
        # Check parameters
        self.assertTrue(os.path.exists(self.ssh_keyscan_parms_file))
        with open(self.ssh_keyscan_parms_file, "r") as fd:
            parms = fd.read()
            fd.close()
        self.assertEqual(parms, self.SSH_KEYSCAN_PARMS % (port, hostname))

    def test_02_add_known_host(self):
        ssh = sshcontroller.SSHController()
        hostname = "localhost"
        port = "2022"
        hostname2 = "anotherhost"
        port2 = "22"
        ssh.add_to_known_hosts(self.known_hosts_file, hostname, port)
        # Check known hosts file exists
        self.assertTrue(os.path.exists(self.known_hosts_file))
        with open(self.known_hosts_file, "r") as fd:
            keys = fd.read()
            fd.close()
        # Check keys data
        self.assertEqual(keys, self.SSH_KEYSCAN_OUTPUT % hostname)
        # Add another host
        ssh.add_to_known_hosts(self.known_hosts_file, hostname2, port2)
        with open(self.known_hosts_file, "r") as fd:
            keys = fd.read()
            fd.close()
        # Check keys data
        self.assertEqual(
            keys,
            self.SSH_KEYSCAN_OUTPUT % hostname + self.SSH_KEYSCAN_OUTPUT % hostname2,
        )

    def test_03_check_known_host(self):
        ssh = sshcontroller.SSHController()
        hostname = "localhost"
        port = "2022"
        hostname2 = "anotherhost"
        port2 = "22"
        # Check inexistent known hosts file
        result = ssh.check_known_host(self.known_hosts_file, hostname)
        self.assertFalse(result)
        # Check empty known hosts file
        open(self.known_hosts_file, "w").close()
        self.assertTrue(os.path.exists(self.known_hosts_file))
        result = ssh.check_known_host(self.known_hosts_file, hostname)
        self.assertFalse(result)
        # Add some hosts to known_hosts_file
        ssh.add_to_known_hosts(self.known_hosts_file, hostname, port)
        ssh.add_to_known_hosts(self.known_hosts_file, hostname2, port2)
        # Check known hosts file for inexistent host
        result = ssh.check_known_host(self.known_hosts_file, "inexistenthost")
        self.assertFalse(result)
        # Check known hosts file for existent host
        result = ssh.check_known_host(self.known_hosts_file, hostname)
        self.assertTrue(result)

    def test_04_get_fingerprint_from_key_data(self):
        ssh = sshcontroller.SSHController()
        key_data = "KEY DATA"
        fprints = ssh.get_fingerprint_from_key_data(key_data)
        self.assertEqual(fprints, self.SSH_KEYGEN_FINGERPRINT_OUTPUT)

    def test_05_get_host_fingerprint(self):
        ssh = sshcontroller.SSHController()
        hostname = "localhost"
        port = "2022"
        fprints = ssh.get_host_fingerprint(hostname, port)
        self.assertEqual(fprints, self.SSH_KEYGEN_FINGERPRINT_OUTPUT)

    def test_06_execute_remote_command(self):
        ssh = sshcontroller.SSHController()
        username = "testuser"
        hostname = "localhost"
        port = "2022"
        command = "mycommand"
        ssh.execute_remote_command(
            command,
            self.private_key_file,
            username,
            hostname,
            port,
            # Extra options
            UserKnownHostsFile=self.known_hosts_file,
        )

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            parms = fd.read().strip()

        self.assertEqual(
            parms,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=command,
                username=username,
                hostname=hostname,
                port=port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_07_open_tunnel(self):
        ssh = sshcontroller.SSHController()
        local_port = "2000"
        tunnel_host = "192.168.0.2"
        tunnel_port = "2020"
        local_forward = "{local_port}:{host}:{tunnel_port}".format(
            local_port=local_port,
            host=tunnel_host,
            tunnel_port=tunnel_port,
        )
        username = "testuser"
        hostname = "localhost"
        port = "2022"

        # Open tunnel without specifying a local host
        ssh.open_tunnel(
            local_forward=local_forward,
            private_key_file=self.private_key_file,
            username=username,
            hostname=hostname,
            port=port,
            # Extra options
            UserKnownHostsFile=self.known_hosts_file,
        )

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file, "r") as fd:
            parms = fd.read().strip()

        self.assertEqual(
            parms,
            SSH_TUNNEL_OPEN_PARMS.format(
                local_forward=f"{local_port}:{tunnel_host}:{tunnel_port}",
                username=username,
                user_home=os.path.expanduser("~"),
                hostname=hostname,
                port=port,
                private_key_file=self.private_key_file,
                known_hosts_file=self.known_hosts_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_08_close_tunnel(self):
        ssh = sshcontroller.SSHController()
        username = "testuser"
        hostname = "localhost"
        port = "2022"

        ssh.close_tunnel(
            private_key_file=self.private_key_file,
            username=username,
            hostname=hostname,
            port=port,
            # Extra options
            UserKnownHostsFile=self.known_hosts_file,
        )

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            parms = fd.read().strip()

        self.assertEqual(
            parms,
            SSH_TUNNEL_CLOSE_PARMS.format(
                username=username,
                user_home=os.path.expanduser("~"),
                hostname=hostname,
                port=port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_09_install_pubkey(self):
        ssh = sshcontroller.SSHController()
        # Change ssh command for session mocking
        ssh.SSH_COMMAND = "ssh-session-mock"
        # Use bad credentials
        with self.assertRaisesRegex(
            sshcontroller.SSHControllerException, "Invalid credentials"
        ):
            ssh.install_pubkey("PUBKEY", "username", "badpassword", "localhost", 22)

        # Use correct credentials (no exception raising)
        ssh.install_pubkey("PUBKEY", "username", "password", "localhost", 22)


if __name__ == "__main__":
    unittest.main()
