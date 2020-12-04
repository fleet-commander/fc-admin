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
from unittest.mock import patch
import os
import tempfile
import shutil
import unittest
import logging

from tests import libvirtmock

from fleetcommander import libvirtcontroller
from fleetcommander.libvirtcontroller import LibVirtControllerException
from tests import (
    SSH_TUNNEL_OPEN_PARMS,
    SSH_TUNNEL_CLOSE_PARMS,
    SSH_REMOTE_COMMAND_PARMS,
)

logger = logging.getLogger(os.path.basename(__file__))

# Mocking assignments
libvirtcontroller.libvirt = libvirtmock.LibvirtModuleMocker


class TestLibVirtControllerCommon(unittest.TestCase):
    """Negative scenarios for common LibVirtController."""

    def setUp(self):
        self.config = {
            "viewer_type": "spice_html5",
            "data_path": "/somepath",
            "username": "testuser",
            "hostname": "localhost",
            "mode": "system",
        }

    def test_invalid_viewer(self):
        badconfig = self.config.copy()
        badconfig["viewer_type"] = "unknown_type"
        with self.assertRaisesRegex(
            LibVirtControllerException, r"^Unsupported libvirt viewer type\."
        ):
            libvirtcontroller.controller(**badconfig)

    def test_invalid_mode(self):
        badconfig = self.config.copy()
        badconfig["mode"] = "unknown_mode"
        with self.assertRaisesRegex(
            LibVirtControllerException, r"^Invalid libvirt mode selected\."
        ):
            libvirtcontroller.controller(**badconfig)


class TestLibVirtController:
    """Base class for LibVirtController."""

    maxDiff = None

    LIBVIRT_MODE = None
    VIEWER = None

    def setUp(self):

        self.test_directory = tempfile.mkdtemp(
            prefix="fc-libvirt-test-%s-" % self.LIBVIRT_MODE
        )

        self.config = {
            "viewer_type": self.VIEWER,
            "data_path": self.test_directory,
            "username": "testuser",
            "hostname": "localhost",
            "mode": self.LIBVIRT_MODE,
        }

        self.known_hosts_file = os.path.join(self.test_directory, "known_hosts")
        self.private_key_file = os.path.join(self.test_directory, "id_rsa")

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
        ctrlr = libvirtcontroller.controller(**config)
        # Set controller delays to 0  for faster testing
        ctrlr.SESSION_START_TRIES_DELAY = 0
        ctrlr.DOMAIN_UNDEFINE_TRIES_DELAY = 0
        ctrlr.known_hosts_file = self.known_hosts_file
        return ctrlr

    def test_video_driver_virtio(self):
        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_video_driver()

        # Fist check for virtio driver

        # Check SSH command
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._VIDEO_DRIVER_CMD,
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )
        self.assertEqual(ctrlr._libvirt_video_driver, "virtio")

    def test_video_driver_qxl(self):
        # Set environment variable to force QXL test
        os.environ["FC_TEST_USE_QXL"] = "1"

        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_video_driver()

        # Check SSH command
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._VIDEO_DRIVER_CMD,
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )
        self.assertEqual(ctrlr._libvirt_video_driver, "qxl")

    def test_session_stop(self):
        ctrlr = self.get_controller(self.config)
        session_params = ctrlr.session_start(libvirtmock.TEST_UUID_ORIGIN)

        ctrlr.session_stop(session_params.domain)

        # Check domain has been stopped and has been set as transient
        # pylint: disable=no-member
        self.assertFalse(ctrlr._last_stopped_domain.active)
        self.assertTrue(ctrlr._last_stopped_domain.transient)
        # pylint: enable=no-member

        # Test SSH tunnel close
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_TUNNEL_CLOSE_PARMS.format(
                username=self.config["username"],
                user_home=os.path.expanduser("~"),
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )


class TestLibVirtControllerSystem(TestLibVirtController):
    LIBVIRT_MODE = "system"

    def test_libvirtd_socket(self):
        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_socket()

        # No command is executed
        self.assertFalse(os.path.exists(self.ssh_parms_file))
        self.assertEqual(ctrlr._libvirt_socket, "")

    def test_list_domains(self):
        ctrlr = self.get_controller(self.config)

        domains = ctrlr.list_domains()
        self.assertListEqual(
            domains,
            [
                {
                    "uuid": libvirtmock.TEST_UUID_ORIGIN,
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
                    "uuid": libvirtmock.TEST_UUID_TEMPORARY_SPICE_HTML5,
                    "name": "Fedora - Fleet Commander temporary session",
                    "active": True,
                    "temporary": True,
                },
                {
                    "uuid": libvirtmock.TEST_UUID_TEMPORARY_SPICE_DIRECT,
                    "name": "Fedora - Fleet Commander temporary session",
                    "active": True,
                    "temporary": True,
                },
            ],
        )

        # Check remote machine environment preparation
        # No command is executed
        self.assertEqual(ctrlr._libvirt_socket, "")
        self.assertEqual(ctrlr._libvirt_video_driver, "virtio")


class TestLibVirtControllerSession(TestLibVirtController):
    LIBVIRT_MODE = "session"

    def test_libvirtd_socket(self):
        ctrlr = self.get_controller(self.config)
        ctrlr._get_libvirt_socket()

        # Check SSH command
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._SESSION_SOCKET_CMD.format(
                    socket=ctrlr.DEFAULT_LIBVIRTD_SOCKET,
                ),
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )
        self.assertEqual(ctrlr._libvirt_socket, "/run/user/1000/libvirt/libvirt-sock")

    def test_list_domains(self):
        ctrlr = self.get_controller(self.config)

        domains = ctrlr.list_domains()
        self.assertListEqual(
            domains,
            [
                {
                    "uuid": libvirtmock.TEST_UUID_ORIGIN,
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
                    "uuid": libvirtmock.TEST_UUID_TEMPORARY_SPICE_HTML5,
                    "name": "Fedora - Fleet Commander temporary session",
                    "active": True,
                    "temporary": True,
                },
                {
                    "uuid": libvirtmock.TEST_UUID_TEMPORARY_SPICE_DIRECT,
                    "name": "Fedora - Fleet Commander temporary session",
                    "active": True,
                    "temporary": True,
                },
            ],
        )

        # Check remote machine environment preparation
        self.assertEqual(ctrlr._libvirt_socket, "/run/user/1000/libvirt/libvirt-sock")
        self.assertEqual(ctrlr._libvirt_video_driver, "virtio")


class TestLibVirtControllerHTML5(TestLibVirtController):
    VIEWER = "spice_html5"

    def test_session_start(self):
        ctrlr = self.get_controller(self.config)

        runtimedir = os.environ.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
        local_socket = os.path.join(runtimedir, "fc-logger.socket")
        ticket = "Secret123"

        # spice ticket is generated the only time
        with patch.object(
            libvirtcontroller.LibVirtController,
            "generate_spice_ticket",
            return_value=ticket,
        ):
            session_params = ctrlr.session_start(libvirtmock.TEST_UUID_ORIGIN)

        self.assertEqual(session_params.domain, ctrlr._last_started_domain.UUIDString())
        self.assertDictEqual(
            session_params.details,
            {
                "host": "localhost",
                "path": local_socket,
                "viewer": self.VIEWER,
                "ticket": ticket,
            },
        )

        # Test new domain XML generation
        new_domain = ctrlr._last_started_domain

        self.assertEqual(
            new_domain.XMLDesc(),
            libvirtmock.XML_MODIF_HTML5.strip()
            % {
                "name-uuid": new_domain.UUIDString()[:8],
                "uuid": new_domain.UUIDString(),
            },
        )

        # Test SSH tunnel opening
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_TUNNEL_OPEN_PARMS.format(
                local_forward=f"{local_socket}:localhost:5900",
                username=self.config["username"],
                user_home=os.path.expanduser("~"),
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        "StreamLocalBindUnlink=yes",
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )


class TestLibVirtControllerDirect(TestLibVirtController):
    VIEWER = "spice_remote_viewer"

    def test_session_start(self):
        ctrlr = self.get_controller(self.config)

        ticket = "Secret123"
        local_runtimedir = os.environ.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
        local_socket = os.path.join(local_runtimedir, "fc-logger.socket")
        remote_runtimedir = "/run/user/1001"

        # spice ticket is generated the only time
        with patch.object(
            libvirtcontroller.LibVirtController,
            "generate_spice_ticket",
            return_value=ticket,
        ):
            session_params = ctrlr.session_start(libvirtmock.TEST_UUID_ORIGIN)

        self.assertEqual(session_params.domain, ctrlr._last_started_domain.UUIDString())

        self.assertDictEqual(
            session_params.details,
            {
                "host": "localhost",
                "viewer": self.VIEWER,
                "notify_socket": local_socket,
                "ca_cert": "FAKE_CA_CERT",
                "cert_subject": "CN=localhost",
                "tls_port": "5900",
                "ticket": ticket,
            },
        )

        new_domain = ctrlr._last_started_domain
        remote_socket = os.path.join(
            remote_runtimedir,
            "fc-{}.socket".format(new_domain.UUIDString()[:8]),
        )

        # Test new domain XML generation
        self.assertEqual(
            new_domain.XMLDesc(),
            libvirtmock.XML_MODIF_DIRECT.strip()
            % {
                "name-uuid": new_domain.UUIDString()[:8],
                "uuid": new_domain.UUIDString(),
                "runtimedir": remote_runtimedir,
            },
        )

        # Test SSH tunnel opening
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_TUNNEL_OPEN_PARMS.format(
                local_forward=(f"{local_socket}:{remote_socket}"),
                username=self.config["username"],
                user_home=os.path.expanduser("~"),
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        "StreamLocalBindUnlink=yes",
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_ca_cert(self):
        ctrlr = self.get_controller(self.config)

        ca_cert = ctrlr._get_spice_ca_cert()
        self.assertEqual(ca_cert, "FAKE_CA_CERT")

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._SPICE_CA_CERT_CMD.format(
                    ca=ctrlr.SPICE_CA_CERT,
                ),
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_remote_user_runtimedir(self):
        ctrlr = self.get_controller(self.config)

        remote_runtimedir = ctrlr._get_user_runtime_dir()
        self.assertEqual(remote_runtimedir, "/run/user/1001")

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._XDG_RUNTIMEDIR_CMD,
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )

    def test_spice_cert_subject(self):
        ctrlr = self.get_controller(self.config)

        spice_cert_subject = ctrlr._get_spice_cert_subject()
        self.assertEqual(spice_cert_subject, "CN=localhost")

        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file) as fd:
            command = fd.read().strip()

        self.assertEqual(
            command,
            SSH_REMOTE_COMMAND_PARMS.format(
                command=ctrlr._SPICE_CERT_SUBJ_CMD.format(cert=ctrlr.SPICE_CERT),
                username=self.config["username"],
                hostname=self.config["hostname"],
                port=ctrlr.ssh_port,
                private_key_file=self.private_key_file,
                optional_args=" ".join(
                    [
                        "-o",
                        f"UserKnownHostsFile={self.known_hosts_file}",
                    ]
                ),
            ),
        )


class TestLibVirtControllerSystemHTML5(
    TestLibVirtControllerSystem, TestLibVirtControllerHTML5, unittest.TestCase
):
    """Test LibVirtController with spice_html5 viewer at system mode."""


class TestLibVirtControllerSystemDirect(
    TestLibVirtControllerSystem, TestLibVirtControllerDirect, unittest.TestCase
):
    """Test LibVirtController with spice_remote_viewer viewer at system mode."""


class TestLibVirtControllerSessionHTML5(
    TestLibVirtControllerSession, TestLibVirtControllerHTML5, unittest.TestCase
):
    """Test LibVirtController with spice_html5 viewer at session mode."""


class TestLibVirtControllerSessionDirect(
    TestLibVirtControllerSession, TestLibVirtControllerDirect, unittest.TestCase
):
    """Test LibVirtController with spice_remote_viewer viewer at session mode."""


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
