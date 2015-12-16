#!/usr/bin/python
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

import os
import sys
import time
import tempfile
import shutil
import unittest
from libvirtcontrollermock import XML_MODIF, XML_NO_SPICE
from libvirtcontrollermock import LibvirtModuleMocker, LibvirtConnectionMocker, LibvirtDomainMocker

sys.path.append(os.path.join(os.environ['TOPSRCDIR'], 'admin'))

from fleetcommander import libvirtcontroller


class TestLibVirtControllerSystemMode(unittest.TestCase):

    config = {
        'data_path': tempfile.mkdtemp(prefix='fc-libvirt-test'),
        'username': 'testuser',
        'hostname': 'localhost',
        'mode': 'system',
        'admin_hostname': 'localhost',
        'admin_port': 8008,
    }

    @classmethod
    def setUpClass(cls):
        # Mock libvirt module
        libvirtcontroller.libvirt = LibvirtModuleMocker()
        cls.ctrlr = libvirtcontroller.LibVirtController(**cls.config)
        # Set controller delays to 0  for faster testing
        cls.ctrlr.SESSION_START_TRIES_DELAY = 0
        cls.ctrlr.DOMAIN_UNDEFINE_TRIES_DELAY = 0
        # Prepare paths for command output files
        cls.ssh_keyscan_parms_file = os.path.join(cls.config['data_path'], 'ssh-keyscan-parms')
        cls.ssh_parms_file = os.path.join(cls.config['data_path'], 'ssh-parms')
        cls.test_directory = cls.config['data_path']
        os.environ['FC_TEST_DIRECTORY'] = cls.test_directory

    @classmethod
    def tearDownClass(cls):
        # Remove test directory
        shutil.rmtree(cls.config['data_path'])

    def test_00_create_keys(self):
        self.ctrlr._generate_ssh_keypair()
        self.assertTrue(os.path.exists(self.ctrlr.private_key_file))
        self.assertTrue(os.path.exists(self.ctrlr.public_key_file))

    def test_01_check_known_hosts(self):
        self.ctrlr._check_known_host()
        self.assertTrue(os.path.exists(self.ssh_keyscan_parms_file))

        with open(self.ssh_keyscan_parms_file, 'r') as fd:
            parms = fd.read()
            fd.close()
        self.assertEqual(parms, 'localhost\n')

        with open(self.ctrlr.known_hosts_file, 'r') as fd:
            known_hosts_contents = fd.read()
            fd.close()
        self.assertEqual(known_hosts_contents, 'localhost ssh-rsa KEY\n')

    def test_02_check_environment_preparation(self):
        socket = self.ctrlr._prepare_remote_env()
        time.sleep(.1)  # Wait for file contents being written
        self.assertTrue(os.path.exists(self.ssh_parms_file))
        with open(self.ssh_parms_file, 'r') as fd:
            command = fd.read()
            fd.close()

        if self.ctrlr.mode == 'system':
            self.assertEqual(socket, '')
            self.assertEqual(command, '-i %(tmpdir)s/id_rsa -o UserKnownHostsFile=%(tmpdir)s/known_hosts -o PreferredAuthentications=publickey -o PasswordAuthentication=no testuser@localhost virsh list > /dev/null\n' % {
                'tmpdir': self.test_directory,
            })
        else:
            self.assertEqual(socket, '/run/user/1000/libvirt/libvirt-sock')
            self.assertEqual(command, '-i %(tmpdir)s/id_rsa -o UserKnownHostsFile=%(tmpdir)s/known_hosts -o PreferredAuthentications=publickey -o PasswordAuthentication=no testuser@localhost virsh list > /dev/null && echo $XDG_RUNTIME_DIR/libvirt/libvirt-sock && [ -S $XDG_RUNTIME_DIR/libvirt/libvirt-sock ]\n' % {
                'tmpdir': self.test_directory,
            })

    def test_03_connect(self):
        self.assertEqual(self.ctrlr.conn, None)
        self.ctrlr._connect()
        self.assertIsInstance(self.ctrlr.conn, LibvirtConnectionMocker)
        # Check connection URI
        if self.ctrlr.mode == 'system':
            uri = 'qemu+libssh2://testuser@localhost/system?keyfile=%(tmpdir)s/id_rsa&known_hosts=%(tmpdir)s/known_hosts&no_tty=1&sshauth=privkey' % {
                'tmpdir': self.test_directory,
            }
        else:
            uri = 'qemu+libssh2://testuser@localhost/session?keyfile=%(tmpdir)s/id_rsa&known_hosts=%(tmpdir)s/known_hosts&no_tty=1&socket=/run/user/1000/libvirt/libvirt-sock&sshauth=privkey' % {
                'tmpdir': self.test_directory,
            }
        self.assertEqual(self.ctrlr.conn.connection_uri, uri)

    def test_04_list_domains(self):
        domains = self.ctrlr.list_domains()
        self.assertEqual(domains, [{'uuid': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'name': 'fedora-unkno'}])

    def test_05_generate_new_domain_xml(self):
        origxml = self.ctrlr.conn.domains[0].XMLDesc()
        newxml = self.ctrlr._generate_new_domain_xml(origxml)
        newdomain_uuid = LibvirtDomainMocker(newxml).UUIDString()
        self.assertEqual(newxml, XML_MODIF % {'uuid': newdomain_uuid})

    def test_06_get_spice_parms(self):
        fakedomain = LibvirtDomainMocker(XML_MODIF)
        host, port = self.ctrlr._get_spice_parms(fakedomain)
        self.assertEqual(host, '127.0.0.1')
        self.assertEqual(port, '5900')
        # Test fail getting spice parameters
        nospicedomain = LibvirtDomainMocker(XML_NO_SPICE)
        self.assertRaises(libvirtcontroller.LibVirtControllerException, self.ctrlr._get_spice_parms, nospicedomain)

    def test_07_open_ssh_tunnel(self):
        port, pid = self.ctrlr._open_ssh_tunnel('127.0.0.1', '5900')
        time.sleep(.1)  # Wait for file contents being written
        with open(self.ssh_parms_file, 'r') as fd:
            os.fsync(fd)
            command = fd.read()
            fd.close()
        self.assertEqual(command, '-i %(tmpdir)s/id_rsa -o UserKnownHostsFile=%(tmpdir)s/known_hosts -o PreferredAuthentications=publickey -o PasswordAuthentication=no testuser@localhost -L %(port)s:127.0.0.1:5900 -N\n' % {
            'tmpdir': self.test_directory,
            'port': port,
        })

    def test_08_undefine_domain(self):
        fakedomain = LibvirtDomainMocker(XML_MODIF)
        self.ctrlr._undefine_domain(fakedomain)
        self.assertTrue(fakedomain.transient)

    def test_09_start_stop(self):
        # Just test start and stop execution
        uuid, port, pid = self.ctrlr.session_start('e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81')
        # We pass None as PID to avoid killing any process.
        self.ctrlr.session_stop(uuid, None)


class TestLibVirtControllerSessionMode(TestLibVirtControllerSystemMode):
    config = {
        'data_path': tempfile.mkdtemp(prefix='fc-libvirt-test'),
        'username': 'testuser',
        'hostname': 'localhost',
        'mode': 'session',
        'admin_hostname': 'localhost',
        'admin_port': 8008,
    }


if __name__ == '__main__':
    unittest.main()
