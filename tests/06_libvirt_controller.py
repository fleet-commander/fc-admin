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
import unittest

sys.path.append(os.path.join(os.environ['TOPSRCDIR'], 'admin'))

from fleetcommander.libvirtcontroller import LibVirtController


class LibvirtModuleMocker(object):

    @staticmethod
    def open(connection_uri):
        # Check connection connection URI
        # Return a LibvirtConnectionMocker
        return LibvirtConnectionMocker()


class LibvirtConnectionMocker(object):
    """
    Class for mocking libvirt connection
    """
    def __init__(self):

        # Load XML data for test domain
        with fd as open(os.path.join('.', 'data/libvirt_domain-orig.xml')):
            xmldata = fd.read()
            fd.close()

        self.domains = [
            LibvirtDomainMocker(xmldata)
        ]

    def listAllDomains(self):
        return self.domains

    def createXML(self, xmldata):
        return LibvirtDomainMocker(xmldata)

    def lookupByUUIDString(self, identifier):
        for domain in self.domains:
            if domain.UUIDString() == identifier:
                return domain
        return None


class LibvirtDomainMocker(object):
    """
    Class for mocking libvirt domain
    """
    def __init__(xmldata):
        self.xmldata = xmldata

    def UUIDString(self):
        pass

    def name(self):
        pass

    def XMLDesc(self):
        return self.xmldata

    def undefine(self):
        pass


class TestLibVirtController(unittest.TestCase):

    config = {
        'data_path': '/tmp/fc-libvirt-test',
        'username': 'testuser',
        'hostname': 'localhost',
        'admin_hostname': 'localhost',
        'admin_port': 8008,
    }

    @classmethod
    def setUpClass(cls):
        cls.ctrlr = LibVirtController(**cls.config)
        # Clear all files to avoid false positives
        cls.tearDownClass()

    @classmethod
    def tearDownClass(cls):
        # Remove key files and other data
        files = [
            cls.ctrlr.private_key_file,
            cls.ctrlr.public_key_file,
            cls.ctrlr.known_hosts_file,
        ]
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    def test_00_create_keys(self):
        self.ctrlr._generate_ssh_keypair()
        self.assertTrue(os.path.exists(self.ctrlr.private_key_file))
        self.assertTrue(os.path.exists(self.ctrlr.public_key_file))

    def test_01_check_environment_preparation(self):
        pass

    def test_02_listdomains(self):
        pass

    def test_03_start(self):
        pass

    def test_04_stop(self):
        pass

if __name__ == '__main__':
    unittest.main()
