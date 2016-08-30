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

from fleetcommander import database, collectors

DCONF_CHANGE = {
    'key': '/foo/bar',
    'value': False,
    'signature': 'b'
}


class BaseCollectorTest(unittest.TestCase):

    COLLECTOR_CLASS = collectors.BaseCollector
    BASIC_CHANGE = DCONF_CHANGE

    def setUp(self):
        # Initialize memory database
        self.db = database.DBManager(':memory:')
        self.collector = self.COLLECTOR_CLASS(self.db)

    def generate_changes(self, keys, handle=True):
        changes = []
        for key in keys:
            change = self.BASIC_CHANGE.copy()
            change['key'] = key
            if handle:
                self.collector.handle_change(change)
            changes.append(change)
        return changes

    def test_00_get_key_from_change(self):
        key = self.collector.get_key_from_change(self.BASIC_CHANGE)
        self.assertEqual(key, self.BASIC_CHANGE['key'])

    def test_01_get_value_from_change(self):
        value = self.collector.get_value_from_change(self.BASIC_CHANGE)
        self.assertEqual(value, self.BASIC_CHANGE['value'])

    def test_02_handle_change(self):
        # Handling of an invalid change is ignored
        invalid_change = self.BASIC_CHANGE.copy()
        del(invalid_change['key'])
        self.collector.handle_change(invalid_change)
        # Check database
        changes = self.db.sessionsettings.get_for_collector(
            self.collector.COLLECTOR_NAME)
        self.assertEqual(changes, {})

        # Handling of a valid change saves it to database
        self.collector.handle_change(self.BASIC_CHANGE)
        # Check database
        changes = self.db.sessionsettings.get_for_collector(
            self.collector.COLLECTOR_NAME)
        self.assertEqual(changes, {
            self.BASIC_CHANGE['key']: json.dumps(self.BASIC_CHANGE),
        })

    def test_03_dump_changes(self):
        # Dump empty collector
        dump = self.collector.dump_changes()
        self.assertEqual(dump, [])

        # Add a change
        self.collector.handle_change(self.BASIC_CHANGE)
        dump = self.collector.dump_changes()
        self.assertEqual(dump, [
            [self.BASIC_CHANGE['key'], self.BASIC_CHANGE['value']]
        ])

    def test_04_remember_selected(self):
        # Add some changes
        change1, change2, change3 = self.generate_changes(
            ['/foo/bar', '/bar/baz', '/baz/foo'])
        # Select some changes
        selected = ['/foo/bar', '/baz/foo']
        self.collector.remember_selected(selected)
        # Check database
        changes = self.db.sessionsettings.get_for_collector(
            self.collector.COLLECTOR_NAME, only_selected=True)
        self.assertEqual(
            changes,
            {
                change1['key']: json.dumps(change1),
                change3['key']: json.dumps(change3),
            })

    def test_05_get_settings(self):
        # Add some changes
        change1, change2, change3 = self.generate_changes(
            ['/foo/bar', '/bar/baz', '/baz/foo'])
        # Select some changes
        selected = ['/foo/bar', '/baz/foo']
        self.collector.remember_selected(selected)
        # Get selected changes
        changes = self.collector.get_settings()
        changes.sort()
        expected = [change1, change3]
        expected.sort()
        self.assertEqual(changes, expected)

    def test_06_merge_settings(self):
        # Add some changes and select them
        keys = ['/foo/bar', '/bar/baz', '/baz/foo']
        change1, change2, change3 = self.generate_changes(keys)
        self.collector.remember_selected(keys)

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(
            ['/foo/bar', '/baz/foo', '/bar/foo'], handle=False)
        change1b['value'] = True
        change3b['value'] = True
        mergewith = [change1b, change3b, change4]

        merged = self.collector.merge_settings(mergewith)
        merged.sort()
        expected = [change1, change2, change3, change4]
        expected.sort()

        self.assertEqual(len(merged), 4)
        self.assertEqual(merged, expected)


if __name__ == '__main__':
    unittest.main()
