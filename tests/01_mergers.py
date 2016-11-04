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

from fleetcommander import mergers


class BaseMergerTest(unittest.TestCase):

    MERGER_CLASS = mergers.BaseChangeMerger
    BASIC_CHANGE = {
        'key': '/foo/bar',
        'value': False,
        'signature': 'b'
    }
    KEY_NAME = 'key'
    KEY_LIST = ['/foo/bar', '/bar/baz', '/baz/foo']

    def setUp(self):
        self.merger = self.MERGER_CLASS()

    def generate_changes(self, keys=None):
        if keys is None:
            keys = self.KEY_LIST
        changes = []
        for key in keys:
            change = self.BASIC_CHANGE.copy()
            change[self.KEY_NAME] = key
            changes.append(change)
        return changes

    def generate_changesets(self):
        # Generate a changeset
        change1, change2, change3 = self.generate_changes()

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(
            ['/foo/bar', '/baz/foo', '/bar/foo'])
        change1b['value'] = True
        change3b['value'] = True

        changeset1 = [change1, change2, change3]
        changeset2 = [change1b, change3b, change4]
        return (changeset1, changeset2)

    def test_01_merge(self):
        changeset1, changeset2 = self.generate_changesets()

        merged = self.merger.merge(changeset1, changeset2)
        merged.sort()
        expected = [changeset2[0], changeset1[1], changeset2[1], changeset2[2]]
        expected.sort()

        self.assertEqual(len(merged), 4)
        self.assertEqual(merged, expected)


class NetworkManagerChangeMergerTest(BaseMergerTest):

    MERGER_CLASS = mergers.NetworkManagerChangeMerger
    BASIC_CHANGE = {
        'uuid': 'foo-uuid',
        'type': 'vpn',
        'id': 'Connection ID',
        'data': 'ENCODED CONNECTION DATA',
    }
    KEY_NAME = 'uuid'
    KEY_LIST = ['foo-uuid', 'bar-uuid', 'baz-uuid']

    def generate_changesets(self):
        # Add some changes and select them
        change1, change2, change3 = self.generate_changes()

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(
            ['foo-uuid', 'baz-uuid', 'waz-uuid'])
        change1b['type'] = 'wifi'
        change3b['type'] = 'eth'

        changeset1 = [change1, change2, change3]
        changeset2 = [change1b, change3b, change4]
        return (changeset1, changeset2)


if __name__ == '__main__':
    unittest.main()
