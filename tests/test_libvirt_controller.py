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

from __future__ import absolute_import
import os
import sys
import tempfile
import shutil
import unittest
import logging

from tests import libvirtmock

sys.path.append(os.path.join(os.environ["TOPSRCDIR"], "admin"))

from fleetcommander import libvirtcontroller

# Mocking assignments
libvirtcontroller.libvirt = libvirtmock.LibvirtModuleMocker

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)


class TestLibVirtControllerSystemMode(unittest.TestCase):

    LIBVIRT_MODE = "system"

    def setUp(self):
        self.test_directory = tempfile.mkdtemp(
            prefix="fc-libvirt-test-%s-" % self.LIBVIRT_MODE
        )
        self.maxDiff = None

        self.config = {
            "data_path": self.test_directory,
            "username": "testuser",
            "hostname": "localhost",
            "mode": self.LIBVIRT_MODE,
        }

        self.known_hosts_file = os.path.join(self.test_directory, "known_hosts")

        # Prepare paths for command output files
        self.ssh_parms_file = os.path.join(self.test_directory, "ssh-parms")

        # Set environment for commands execution
        os.environ["FC_TEST_DIRECTORY"] = self.test_directory

        # Set to not use QXL by default in tests
        os.environ["FC_TEST_USE_QXL"] = "0"

    def tearDown(self):
        # Remove test directory
        shutil.rmtree(self.test_directory)

    def get_controller(self, config):
        ctrlr = libvirtcontroller.LibVirtController(**config)
        # Set controller delays to 0  for faster testing
        ctrlr.SESSION_START_TRIES_DELAY = 0
        ctrlr.DOMAIN_UNDEFINE_TRIES_DELAY = 0
        ctrlr.known_hosts_file = self.known_hosts_file
        return ctrlr

    def test_00_initialization(self):
        logging.debug("TEST 00 %s mode", self.LIBVIRT_MODE)

        # Check data path creation
        self.assertTrue(os.path.isdir(self.test_directory))

        # Invalid mode selected
        badconfig = self.config.copy()
        badconfig["data_path"] = os.path.join(
            self.test_directory, "invalidmode_data_path"
        )
        badconfig["mode"] = "invalidmode"
        self.assertRaises(
            libvirtcontroller.LibVirtControllerException,
            libvirtcontroller.LibVirtController,
            **badconfig
        )
        self.assertFalse(os.path.isdir(badconfig["data_path"]))

    def test_01_check_socket(self):
        logging.debug("TEST 01 %s mode", self.LIBVIRT_MODE)

        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_socket()

        if ctrlr.mode == "system":
            # No command is executed
            self.assertFalse(os.path.exists(self.ssh_parms_file))
            self.assertEqual(ctrlr._libvirt_socket, "")
        else:
            # Check SSH command
            self.assertTrue(os.path.exists(self.ssh_parms_file))
            with open(self.ssh_parms_file, "r") as fd:
                command = fd.read()
                fd.close()
            self.assertEqual(
                command,
                "-i %(tmpdir)s/id_rsa "
                "-o PreferredAuthentications=publickey "
                "-o PasswordAuthentication=no "
                "-o UserKnownHostsFile=%(tmpdir)s/known_hosts "
                "testuser@localhost -p %(sshport)s "
                "/usr/sbin/libvirtd -d > /dev/null 2>&1; "
                "echo $XDG_RUNTIME_DIR/libvirt/libvirt-sock "
                "&& [ -S $XDG_RUNTIME_DIR/libvirt/libvirt-sock ]"
                "\n" % {"tmpdir": self.test_directory, "sshport": ctrlr.ssh_port},
            )
            self.assertEqual(
                ctrlr._libvirt_socket, "/run/user/1000/libvirt/libvirt-sock"
            )

    def test_02_check_video_driver_virtio(self):
        logging.debug("TEST 02 %s mode", self.LIBVIRT_MODE)

        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_video_driver()

        # Fist check for virtio driver

        # Check SSH command
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file, "r") as fd:
            command = fd.read()
            fd.close()
        self.assertEqual(
            command,
            "-i %(tmpdir)s/id_rsa "
            "-o PreferredAuthentications=publickey "
            "-o PasswordAuthentication=no "
            "-o UserKnownHostsFile=%(tmpdir)s/known_hosts "
            "testuser@localhost -p %(sshport)s "
            "if [ -x /usr/libexec/qemu-kvm ]; "
            'then cmd="/usr/libexec/qemu-kvm"; '
            'else cmd="/usr/bin/qemu-kvm"; fi ; '
            "$cmd -device help 2>&1 "
            '| grep "virtio-vga" > /dev/null; '
            'if [ $? == 0 ]; then echo "virtio"; '
            'else echo "qxl"; fi'
            "\n" % {"tmpdir": self.test_directory, "sshport": ctrlr.ssh_port},
        )

        self.assertEqual(ctrlr._libvirt_video_driver, "virtio")

    def test_03_check_video_driver_qxl(self):
        logging.debug("TEST 03 %s mode", self.LIBVIRT_MODE)

        # Set environment variable to force QXL test
        os.environ["FC_TEST_USE_QXL"] = "1"

        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_video_driver()

        # Check SSH command
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file, "r") as fd:
            command = fd.read()
            fd.close()
        self.assertEqual(
            command,
            "-i %(tmpdir)s/id_rsa "
            "-o PreferredAuthentications=publickey "
            "-o PasswordAuthentication=no "
            "-o UserKnownHostsFile=%(tmpdir)s/known_hosts "
            "testuser@localhost -p %(sshport)s "
            "if [ -x /usr/libexec/qemu-kvm ]; "
            'then cmd="/usr/libexec/qemu-kvm"; '
            'else cmd="/usr/bin/qemu-kvm"; fi ; '
            "$cmd -device help 2>&1 "
            '| grep "virtio-vga" > /dev/null; '
            'if [ $? == 0 ]; then echo "virtio"; '
            'else echo "qxl"; fi'
            "\n" % {"tmpdir": self.test_directory, "sshport": ctrlr.ssh_port},
        )

        self.assertEqual(ctrlr._libvirt_video_driver, "qxl")

    def test_04_list_domains(self):
        logging.debug("TEST 04 %s mode", self.LIBVIRT_MODE)

        ctrlr = self.get_controller(self.config)

        domains = ctrlr.list_domains()
        self.assertEqual(
            domains,
            [
                {
                    "uuid": libvirtmock.TEST_UUID_SPICE,
                    "name": "Fedora",
                    "active": True,
                    "temporary": False,
                },
                {
                    "uuid": libvirtmock.TEST_UUID_NO_SPICE,
                    "name": "Fedora unspiced",
                    "active": True,
                    "temporary": False,
                },
                {
                    "uuid": libvirtmock.TEST_UUID_TEMPORARY,
                    "name": "Fedora - Fleet Commander temporary session",
                    "active": True,
                    "temporary": True,
                },
            ],
        )

        # Check remote machine environment preparation
        if ctrlr.mode == "system":
            # No command is executed
            self.assertEqual(ctrlr._libvirt_socket, "")
            self.assertEqual(ctrlr._libvirt_video_driver, "virtio")
        else:
            self.assertEqual(
                ctrlr._libvirt_socket, "/run/user/1000/libvirt/libvirt-sock"
            )
            self.assertEqual(ctrlr._libvirt_video_driver, "virtio")

    def test_05_start(self):
        logging.debug("TEST 05 %s mode", self.LIBVIRT_MODE)

        ctrlr = self.get_controller(self.config)
        _uuid, port, _pid = ctrlr.session_start(libvirtmock.TEST_UUID_SPICE)

        # Test new domain XML generation
        new_domain = ctrlr._last_started_domain

        self.assertEqual(
            new_domain.XMLDesc(),
            libvirtmock.XML_MODIF.strip()
            % {
                "name-uuid": new_domain.UUIDString()[:8],
                "uuid": new_domain.UUIDString(),
            },
        )

        # Test SSH tunnel opening
        ctrlr.ssh._tunnel_prog.wait()
        with open(self.ssh_parms_file, "r") as fd:
            command = fd.read()
            fd.close()
        self.assertEqual(
            command,
            "-i %(tmpdir)s/id_rsa -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o UserKnownHostsFile=%(tmpdir)s/known_hosts testuser@localhost -p %(sshport)s -L 127.0.0.1:%(port)s:127.0.0.1:5900 -N\n"
            % {
                "tmpdir": self.test_directory,
                "sshport": ctrlr.ssh_port,
                "port": port,
            },
        )

    def test_06_start_stop(self):
        logging.debug("TEST 06 %s mode", self.LIBVIRT_MODE)

        ctrlr = self.get_controller(self.config)
        uuid, _port, _pid = ctrlr.session_start(libvirtmock.TEST_UUID_SPICE)

        # We pass None as PID to avoid killing any process
        ctrlr.session_stop(uuid, None)

        # Check domain has been stopped and has been set as transient
        # pylint: disable=no-member
        self.assertFalse(ctrlr._last_stopped_domain.active)
        self.assertTrue(ctrlr._last_stopped_domain.transient)
        # pylint: enable=no-member


class TestLibVirtControllerSessionMode(TestLibVirtControllerSystemMode):
    LIBVIRT_MODE = "session"


if __name__ == "__main__":
    unittest.main()
