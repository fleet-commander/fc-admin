#!/usr/bin/python
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
import os
import sys
import shutil
import unittest

import dbus

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

# Fleet commander imports
from fleetcommander import fcdbus


class TestDbusService(unittest.TestCase):

    def setUp(self):
        self.test_directory = os.environ['FC_TEST_DIRECTORY']

        self.args = {
            'data_dir': self.test_directory,
            'state_dir': self.test_directory,
            'database_path': os.path.join(self.test_directory, 'database.db'),
        }

        os.environ['FC_TEST_DIRECTORY'] = self.test_directory

    def tearDown(self):
        shutil.rmtree(self.test_directory)

    def test_00_dbus(self):
        c = fcdbus.FleetCommanderDbusClient(bus=dbus.SessionBus())
        print c.get_public_key()
        raise ZeroDivisionError()

    def test_11_merge_settings(self):

        a = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": False, "signature": "b"}]}
        b = {"org.libreoffice.registry": [{"key": "/org/libreoffice/registry/foo", "value": "asd", "signature": "string"}]}
        c = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": True, "signature": "b"}]}
        d = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": True, "signature": "b"},
                                     {"key": "/foo/bleh", "value": True, "signature": "b"}]}
        ab = fcdbus.merge_settings(a, b)
        ac = fcdbus.merge_settings(a, c)
        aa = fcdbus.merge_settings(a, a)
        ad = fcdbus.merge_settings(a, d)
        an = fcdbus.merge_settings(a, {})

        self.assertEqual(len(ab), 2)
        self.assertTrue("org.gnome.gsettings" in ab)
        self.assertTrue("org.libreoffice.registry" in ab)
        self.assertTrue(len(ac["org.gnome.gsettings"]) == 1)
        self.assertTrue(ac["org.gnome.gsettings"][0]["value"] is True)
        self.assertTrue(len(ad["org.gnome.gsettings"]) == 2)
        self.assertTrue(ad["org.gnome.gsettings"][1]["key"] == "/foo/bar")
        self.assertTrue(ad["org.gnome.gsettings"][0]["key"] == "/foo/bleh")

if __name__ == '__main__':
    unittest.main()
