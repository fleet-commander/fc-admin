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

# Python imports
import sys
import os
import json
import unittest

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

from fleetcommander.database import DBManager


class UnsupportedType(object):
    """
    Unsupported type for testing
    """
    pass


class TestDBManager(unittest.TestCase):

    test_setting = {
        'key': '/foo/bar',
        'schema': 'org.gnome.testkey',
        'value': False
    }

    test_setting_json = json.dumps(test_setting)

    INITIAL_VALUES = {
        'testkeystr': 'strvalue',
        'testkeyunicode': 'unicodevalue',
        'testkeyint': 42,
        'testkeylong': long(42),
        'testkeyfloat': 42.0,
        'testkeytuple': ('foo', 42, 'bar'),
        'testkeylist': ['foo', 42, 'bar'],
        'testkeydict': test_setting
    }

    def setUp(self):
        # Initialize memory database
        self.db = DBManager(':memory:')
        # Add values to config
        for k, v in self.INITIAL_VALUES.items():
            self.db.config[k] = v

    def test_01_config_dictionary_setitem(self):
        # Add unsupported type to config
        self.assertRaises(ValueError, self.db.config.__setitem__, 'unsupported', UnsupportedType())

    def test_02_config_dictionary_getitem(self):
        # Get inexistent value
        self.assertRaises(KeyError,  self.db.config.__getitem__, 'unknownkey')
        # Get existent values
        for k, v in self.INITIAL_VALUES.items():
            self.assertEqual(self.db.config[k], v)
        # Get default values
        self.assertEqual(self.db.config.get('testkeystr', 'defaultvalue'), 'strvalue')
        self.assertEqual(self.db.config.get('unknownkey', 'defaultvalue'), 'defaultvalue')

    def test_03_config_dictionary_itemmembership(self):
        # Set data in config
        self.assertTrue('testkeystr' in self.db.config)
        self.assertFalse('unknownkey' in self.db.config)

    def test_04_config_dictionary_deleteitem(self):
        # Delete values from config
        self.assertTrue('testkeystr' in self.db.config)
        del(self.db.config['testkeystr'])
        self.assertFalse('testkeystr' in self.db.config)

    def test_05_config_dictionary_setdefault(self):
        value = self.db.config.setdefault('testkeystr', 'anotherstrvalue')
        self.assertEqual(self.db.config['testkeystr'], 'strvalue')
        self.assertEqual(value, 'strvalue')
        value = self.db.config.setdefault('anothertestkeystr', 'anotherstrvalue')
        self.assertEqual(self.db.config['anothertestkeystr'], 'anotherstrvalue')
        self.assertEqual(value, 'anotherstrvalue')

    def test_06_config_dictionary_iteration(self):
        items = self.db.config.items()
        self.assertEqual(len([x for x in items]), 8)
        for item in items:
            self.assertEqual(item[1], self.INITIAL_VALUES[item[0]])

if __name__ == '__main__':
    unittest.main()
