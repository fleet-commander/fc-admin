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

# Python imports
from __future__ import absolute_import
import sys
import os
import unittest

PYTHONPATH = os.path.join(os.environ["TOPSRCDIR"], "admin")
sys.path.append(PYTHONPATH)

from fleetcommander import mergers


class BaseMergerTest(unittest.TestCase):

    maxDiff = None

    MERGER_CLASS = mergers.BaseChangeMerger
    BASIC_CHANGE = {"key": "/foo/bar", "value": False, "signature": "b"}
    KEY_NAME = "key"
    KEY_LIST = ["/foo/bar", "/bar/baz", "/baz/foo"]

    def setUp(self):
        self.merger = self.MERGER_CLASS()

    def generate_changes(self, keys=None):
        changes = [{}, {}, {}]

        if keys is None:
            keys = self.KEY_LIST

        if keys:
            changes = []

        for key in keys:
            change = self.BASIC_CHANGE.copy()
            change[self.KEY_NAME] = key
            changes.append(change)

        assert len(changes) == 3
        return changes

    def generate_changesets(self):
        # Generate a changeset
        change1, change2, change3 = self.generate_changes()

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(
            ["/foo/bar", "/baz/foo", "/bar/foo"]
        )
        change1b["value"] = True
        change3b["value"] = True

        changeset1 = [change1, change2, change3]
        changeset2 = [change1b, change3b, change4]
        return (changeset1, changeset2)

    def test_01_merge(self):
        changeset1, changeset2 = self.generate_changesets()

        merged = self.merger.merge(changeset1, changeset2)
        expected = [changeset2[0], changeset1[1], changeset2[1], changeset2[2]]

        self.assertEqual(len(merged), 4)
        self.assertEqual(
            sorted(merged, key=lambda k: k[self.KEY_NAME]),
            sorted(expected, key=lambda k: k[self.KEY_NAME]),
        )


class NetworkManagerChangeMergerTest(BaseMergerTest):

    MERGER_CLASS = mergers.NetworkManagerChangeMerger
    BASIC_CHANGE = {
        "uuid": "foo-uuid",
        "type": "vpn",
        "id": "Connection ID",
        "data": "ENCODED CONNECTION DATA",
    }
    KEY_NAME = "uuid"
    KEY_LIST = ["foo-uuid", "bar-uuid", "baz-uuid"]

    def generate_changesets(self):
        # Add some changes and select them
        change1, change2, change3 = self.generate_changes()

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(
            ["foo-uuid", "baz-uuid", "waz-uuid"]
        )
        change1b["type"] = "wifi"
        change3b["type"] = "eth"

        changeset1 = [change1, change2, change3]
        changeset2 = [change1b, change3b, change4]
        return (changeset1, changeset2)


class ChromiumMergerTest(BaseMergerTest):

    MERGER_CLASS = mergers.ChromiumChangeMerger
    BASIC_CHANGE = {"key": "/foo/bar", "value": False, "signature": "b"}

    KEY_NAME = "key"
    KEY_LIST = [
        "NeverGonnaGiveYouUp",
        "NeverGonnaLetYouDown",
        "NeverGonnaRunAroundAndDesertYou",
    ]

    KEY_LIST_2 = [
        "NeverGonnaGiveYouUp",
        "NeverGonnaRunAroundAndDesertYou",
        "NeverGonnaTellALieAndHurtYou",
    ]

    BOOKMARKS_CHANGE1 = {
        "key": "ManagedBookmarks",
        "value": [
            {
                "name": "Fedora",
                "children": [
                    {"name": "Get Fedora", "url": "https://getfedora.org/"},
                    {
                        "name": "Fedora Project",
                        "url": "https://start.fedoraproject.org/",
                    },
                ],
            },
            {"name": "FreeIPA", "url": "http://freeipa.org"},
            {
                "name": "Fleet Commander Github",
                "url": "https://github.com/fleet-commander/",
            },
        ],
    }

    BOOKMARKS_CHANGE2 = {
        "key": "ManagedBookmarks",
        "value": [
            {
                "name": "Fedora",
                "children": [
                    {"name": "Get Fedora NOW!!!", "url": "https://getfedora.org/"},
                    {
                        "name": "Fedora Project",
                        "url": "https://start.fedoraproject.org/",
                    },
                    {
                        "name": "The Chromium Projects",
                        "url": "https://www.chromium.org/",
                    },
                    {"name": "SSSD", "url": "pagure.org/SSSD"},
                ],
            },
            {"name": "FreeIPA", "url": "http://freeipa.org"},
            {
                "name": "Fleet Commander Docs",
                "url": "http://fleet-commander.org/documentation.html",
            },
        ],
    }

    BOOKMARKS_CHANGE_MERGED = {
        "key": "ManagedBookmarks",
        "value": [
            {
                "name": "Fedora",
                "children": [
                    {"name": "Get Fedora", "url": "https://getfedora.org/"},
                    {
                        "name": "Fedora Project",
                        "url": "https://start.fedoraproject.org/",
                    },
                    {"name": "Get Fedora NOW!!!", "url": "https://getfedora.org/"},
                    {
                        "name": "The Chromium Projects",
                        "url": "https://www.chromium.org/",
                    },
                    {"name": "SSSD", "url": "pagure.org/SSSD"},
                ],
            },
            {"name": "FreeIPA", "url": "http://freeipa.org"},
            {
                "name": "Fleet Commander Github",
                "url": "https://github.com/fleet-commander/",
            },
            {
                "name": "Fleet Commander Docs",
                "url": "http://fleet-commander.org/documentation.html",
            },
        ],
    }

    def setUp(self):
        self.merger = self.MERGER_CLASS()

    def generate_changesets(self):
        # Generate a changeset
        change1, change2, change3 = self.generate_changes()

        # Generate some changes for merging
        change1b, change3b, change4 = self.generate_changes(self.KEY_LIST_2)
        change1b["value"] = True
        change3b["value"] = True

        changeset1 = [change1, change2, change3, self.BOOKMARKS_CHANGE1]
        changeset2 = [change1b, change3b, change4, self.BOOKMARKS_CHANGE2]
        return (changeset1, changeset2)

    def test_00_merge_bookmarks(self):
        result = self.merger.merge_bookmarks(
            self.BOOKMARKS_CHANGE1["value"], self.BOOKMARKS_CHANGE2["value"]
        )

        self.assertEqual(result, self.BOOKMARKS_CHANGE_MERGED["value"])

    def test_01_merge(self):
        changeset1, changeset2 = self.generate_changesets()

        merged = self.merger.merge(changeset1, changeset2)
        expected = [
            changeset2[0],
            changeset1[1],
            changeset2[1],
            changeset2[2],
            self.BOOKMARKS_CHANGE_MERGED,
        ]

        self.assertEqual(len(merged), 5)
        self.assertEqual(
            sorted(merged, key=lambda k: k[self.KEY_NAME]),
            sorted(expected, key=lambda k: k[self.KEY_NAME]),
        )


if __name__ == "__main__":
    unittest.main()
