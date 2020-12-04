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
from __future__ import print_function
import sys
import os
import json
import logging
import unittest

# GObject Introspection imports
from gi.repository import GLib
from gi.repository import Gio

PYTHONPATH = os.path.join(os.environ["TOPSRCDIR"], "logger")
sys.path.append(PYTHONPATH)

import fleet_commander_logger as FleetCommander

logger = logging.getLogger(os.path.basename(__file__))

# Get mainloop
ml = GLib.MainLoop()


# Test helpers


def mainloop_quit_callback(*args, **kwargs):
    logger.error("Timed out waiting for file update notification. Test probably failed")
    ml.quit()


class MockConnectionManager:
    """
    Connection Manager mock class
    """

    def __init__(self):
        self.log = []

    def submit_change(self, namespace, data):
        self.log.append([namespace, data])

    def pop(self):
        return self.log.pop(0)


DEFAULT_LOCAL_STATE_DATA = {"profile": {"last_active_profiles": []}}

DEFAULT_PREFERENCES_1_DATA = {"browser": {"show_home_button": True}}

DEFAULT_PREFERENCES_2_DATA = {"bookmark_bar": {"show_on_all_tabs": False}}

DEFAULT_BOOKMARKS_DATA = {
    "checksum": "ae57f822164f733ef76bee6623fe154b",
    "roots": {
        "bookmark_bar": {
            "children": [
                {
                    "children": [
                        {
                            "date_added": "13162413694565917",
                            "id": "8",
                            "meta_info": {"last_visited_desktop": "13162413694567018"},
                            "name": "Get Fedora",
                            "type": "url",
                            "url": "https://getfedora.org/",
                        },
                        {
                            "date_added": "13162411883407407",
                            "id": "5",
                            "meta_info": {"last_visited_desktop": "13162411883410030"},
                            "name": "Fedora Project",
                            "type": "url",
                            "url": "https://start.fedoraproject.org/",
                        },
                    ],
                    "date_added": "13162413709642660",
                    "date_modified": "13162413767671305",
                    "id": "9",
                    "name": "Fedora",
                    "type": "folder",
                },
                {
                    "date_added": "13162413767671305",
                    "id": "10",
                    "meta_info": {"last_visited_desktop": "13162413767671448"},
                    "name": "The Chromium Projects",
                    "type": "url",
                    "url": "https://www.chromium.org/",
                },
                {
                    "date_added": "13162413825990580",
                    "id": "11",
                    "meta_info": {"last_visited_desktop": "13162413825992055"},
                    "name": "Fleet Commander",
                    "type": "url",
                    "url": "http://fleet-commander.org/",
                },
            ],
            "date_added": "13162411874534262",
            "date_modified": "13162413825990580",
            "id": "1",
            "name": "Bookmarks bar",
            "type": "folder",
        },
        "other": {
            "children": [
                {
                    "date_added": "13162413694565917",
                    "id": "12",
                    "meta_info": {"last_visited_desktop": "13162413694567018"},
                    "name": "Fleet Commander Github",
                    "type": "url",
                    "url": "https://github.com/fleet-commander/",
                }
            ],
            "date_added": "13162411874534270",
            "date_modified": "0",
            "id": "2",
            "name": "Other bookmarks",
            "type": "folder",
        },
        "synced": {
            "children": [],
            "date_added": "13162411874534271",
            "date_modified": "0",
            "id": "3",
            "name": "Mobile bookmarks",
            "type": "folder",
        },
    },
    "version": 1,
}

MODIFIED_BOOKMARKS_DATA = {
    "checksum": "ae57f822164f733ef76bee6623fe154b",
    "roots": {
        "bookmark_bar": {
            "children": [
                {
                    "children": [
                        {
                            "date_added": "13162413694565917",
                            "id": "8",
                            "meta_info": {"last_visited_desktop": "13162413694567018"},
                            "name": "Get Fedora NOW!!!",
                            "type": "url",
                            "url": "https://getfedora.org/",
                        },
                        {
                            "date_added": "13162411883407407",
                            "id": "5",
                            "meta_info": {"last_visited_desktop": "13162411883410030"},
                            "name": "Fedora Project",
                            "type": "url",
                            "url": "https://start.fedoraproject.org/",
                        },
                        {
                            "date_added": "13162413767671305",
                            "id": "10",
                            "meta_info": {"last_visited_desktop": "13162413767671448"},
                            "name": "The Chromium Projects",
                            "type": "url",
                            "url": "https://www.chromium.org/",
                        },
                        {
                            "date_added": "13162413767671305",
                            "id": "14",
                            "meta_info": {"last_visited_desktop": "13162413767671448"},
                            "name": "SSSD",
                            "type": "url",
                            "url": "pagure.org/SSSD",
                        },
                    ],
                    "date_added": "13162413709642660",
                    "date_modified": "13162413767671305",
                    "id": "9",
                    "name": "Fedora",
                    "type": "folder",
                },
                {
                    "date_added": "13162413825990580",
                    "id": "11",
                    "meta_info": {"last_visited_desktop": "13162413825992055"},
                    "name": "Fleet Commander Docs",
                    "type": "url",
                    "url": "http://fleet-commander.org/documentation.html",
                },
                {
                    "date_added": "13162413825990580",
                    "id": "13",
                    "meta_info": {"last_visited_desktop": "13162413825992055"},
                    "name": "FreeIPA",
                    "type": "url",
                    "url": "http://freeipa.org",
                },
            ],
            "date_added": "13162411874534262",
            "date_modified": "13162413825990580",
            "id": "1",
            "name": "Bookmarks bar",
            "type": "folder",
        },
        "other": {
            "children": [
                {
                    "date_added": "13162413694565917",
                    "id": "12",
                    "meta_info": {"last_visited_desktop": "13162413694567018"},
                    "name": "Fleet Commander Github",
                    "type": "url",
                    "url": "https://github.com/fleet-commander/",
                }
            ],
            "date_added": "13162411874534270",
            "date_modified": "0",
            "id": "2",
            "name": "Other bookmarks",
            "type": "folder",
        },
        "synced": {
            "children": [],
            "date_added": "13162411874534271",
            "date_modified": "0",
            "id": "3",
            "name": "Mobile bookmarks",
            "type": "folder",
        },
    },
    "version": 1,
}

PARSED_BOOKMARKS_DATA = [
    json.dumps(
        [["Bookmarks bar", "Fedora"], "8", "https://getfedora.org/", "Get Fedora"],
        sort_keys=True,
    ),
    json.dumps(
        [
            ["Bookmarks bar", "Fedora"],
            "5",
            "https://start.fedoraproject.org/",
            "Fedora Project",
        ],
        sort_keys=True,
    ),
    json.dumps(
        [["Bookmarks bar"], "10", "https://www.chromium.org/", "The Chromium Projects"],
        sort_keys=True,
    ),
    json.dumps(
        [["Bookmarks bar"], "11", "http://fleet-commander.org/", "Fleet Commander"],
        sort_keys=True,
    ),
    json.dumps(
        [
            ["Other bookmarks"],
            "12",
            "https://github.com/fleet-commander/",
            "Fleet Commander Github",
        ],
        sort_keys=True,
    ),
]

DIFFERENCE_BOOKMARKS_DATA = [
    json.dumps(
        [
            ["Bookmarks bar", "Fedora"],
            "8",
            "https://getfedora.org/",
            "Get Fedora NOW!!!",
        ],
        sort_keys=True,
    ),
    json.dumps(
        [
            ["Bookmarks bar", "Fedora"],
            "10",
            "https://www.chromium.org/",
            "The Chromium Projects",
        ],
        sort_keys=True,
    ),
    json.dumps(
        [["Bookmarks bar", "Fedora"], "14", "pagure.org/SSSD", "SSSD"], sort_keys=True
    ),
    json.dumps(
        [
            ["Bookmarks bar"],
            "11",
            "http://fleet-commander.org/documentation.html",
            "Fleet Commander Docs",
        ],
        sort_keys=True,
    ),
    json.dumps(
        [["Bookmarks bar"], "13", "http://freeipa.org", "FreeIPA"], sort_keys=True
    ),
]

DEPLOY_BOOKMARKS_DATA = [
    {
        "name": "Fedora",
        "children": [
            {"name": "Get Fedora", "url": "https://getfedora.org/"},
            {"name": "Fedora Project", "url": "https://start.fedoraproject.org/"},
        ],
    },
    {"name": "The Chromium Projects", "url": "https://www.chromium.org/"},
    {"name": "Fleet Commander", "url": "http://fleet-commander.org/"},
    {"name": "Fleet Commander Github", "url": "https://github.com/fleet-commander/"},
]

DEPLOY_DIFF_BOOKMARKS_DATA = [
    {
        "name": "Fedora",
        "children": [
            {"name": "Get Fedora NOW!!!", "url": "https://getfedora.org/"},
            {"name": "The Chromium Projects", "url": "https://www.chromium.org/"},
            {"name": "SSSD", "url": "pagure.org/SSSD"},
        ],
    },
    {
        "name": "Fleet Commander Docs",
        "url": "http://fleet-commander.org/documentation.html",
    },
    {"name": "FreeIPA", "url": "http://freeipa.org"},
]


class TestChromiumLogger(unittest.TestCase):
    def setUp(self):
        pass

    def setup_test_directory(self, sessions=[], profinit=True, prefsinit=True):
        profile1_prefs = DEFAULT_PREFERENCES_1_DATA
        profile2_prefs = DEFAULT_PREFERENCES_2_DATA
        # Create a temporary directory for testing
        TMPDIR = GLib.dir_make_tmp("fc_logger_chromium_XXXXXX")
        # Create profile directories
        self.assertEqual(
            0, GLib.mkdir_with_parents(os.path.join(TMPDIR, "Profile 1"), 0o755)
        )
        self.assertEqual(
            0, GLib.mkdir_with_parents(os.path.join(TMPDIR, "Profile 2"), 0o755)
        )
        # Create local state file
        local_state_data = DEFAULT_LOCAL_STATE_DATA
        local_state_data["profile"]["last_active_profiles"] = sessions
        with open(os.path.join(TMPDIR, "Local State"), "w") as fd:
            fd.write(json.dumps(local_state_data, sort_keys=True))
        with open(os.path.join(TMPDIR, "Profile 1/Preferences"), "w") as fd:
            fd.write(json.dumps(profile1_prefs, sort_keys=True))
        with open(os.path.join(TMPDIR, "Profile 2/Preferences"), "w") as fd:
            fd.write(json.dumps(profile2_prefs, sort_keys=True))
        # Bookmarks data
        with open(os.path.join(TMPDIR, "Profile 1/Bookmarks"), "w") as fd:
            fd.write(json.dumps(DEFAULT_BOOKMARKS_DATA, sort_keys=True))
        with open(os.path.join(TMPDIR, "Profile 2/Bookmarks"), "w") as fd:
            fd.write(json.dumps(DEFAULT_BOOKMARKS_DATA, sort_keys=True))

        return TMPDIR

    def test_01_local_state_startup(self):
        # Setup test directory
        TMPDIR = self.setup_test_directory(["Profile 1"])

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        self.assertTrue(
            os.path.join(TMPDIR, "Profile 1/Preferences")
            in chromium_logger.monitored_preferences
        )

    def test_02_local_state_monitoring(self):

        # Helper function to simulate file modified notification
        def simulate_filenotification(clogger):
            clogger._local_state_file_updated(
                clogger.file_monitors[clogger.local_state_path],
                Gio.File.new_for_path(clogger.local_state_path),
                None,
                Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            )

        # Setup test directory
        TMPDIR = self.setup_test_directory()

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        # Add a new session to the Local State file
        local_state_data = DEFAULT_LOCAL_STATE_DATA
        local_state_data["profile"]["last_active_profiles"] = ["Profile 1"]
        with open(os.path.join(TMPDIR, "Local State"), "w") as fd:
            fd.write(json.dumps(local_state_data, sort_keys=True))
            fd.close()

        # Simulate a local state file modification
        simulate_filenotification(chromium_logger)

        self.assertTrue(
            os.path.join(TMPDIR, "Profile 1/Preferences")
            in chromium_logger.monitored_preferences
        )

        # Add a new session to the Local State file
        local_state_data["profile"]["last_active_profiles"] = ["Profile 1", "Profile 2"]
        with open(os.path.join(TMPDIR, "Local State"), "w") as fd:
            fd.write(json.dumps(local_state_data, sort_keys=True))
            fd.close()

        # Simulate a local state file modification
        simulate_filenotification(chromium_logger)

        self.assertTrue(
            os.path.join(TMPDIR, "Profile 2/Preferences")
            in chromium_logger.monitored_preferences
        )

    def test_03_get_preference_value(self):
        # Setup test directory
        TMPDIR = self.setup_test_directory()

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        # Existent key
        self.assertEqual(
            True,
            chromium_logger.get_preference_value(
                DEFAULT_PREFERENCES_1_DATA, "browser.show_home_button"
            ),
        )

        # Non existent key
        self.assertEqual(
            None,
            chromium_logger.get_preference_value(
                DEFAULT_PREFERENCES_1_DATA, "nonexistent.key.name"
            ),
        )

    def test_04_bookmarks_parse(self):
        # Setup test directory
        TMPDIR = self.setup_test_directory()
        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        # Check bookmarks tree parsing to policy format
        result = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA)
        self.assertEqual(
            json.dumps(PARSED_BOOKMARKS_DATA, sort_keys=True),
            json.dumps(result, sort_keys=True),
        )

    def test_05_get_modified_bookmarks(self):
        # Setup test directory
        TMPDIR = self.setup_test_directory()
        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        # Parse bookmarks data
        bmarks1 = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA)
        bmarks2 = chromium_logger.parse_bookmarks(MODIFIED_BOOKMARKS_DATA)

        # Check difference with same bookmarks is an empty list
        returned = chromium_logger.get_modified_bookmarks(bmarks1, bmarks1)
        self.assertEqual(
            json.dumps([], sort_keys=True), json.dumps(returned, sort_keys=True)
        )

        # Check difference with different bookmarks data is ok
        returned = chromium_logger.get_modified_bookmarks(bmarks1, bmarks2)
        self.assertEqual(
            json.dumps(DIFFERENCE_BOOKMARKS_DATA, sort_keys=True),
            json.dumps(returned, sort_keys=True),
        )

    def test_06_deploy_bookmarks(self):
        # Setup test directory
        TMPDIR = self.setup_test_directory()

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)
        # Parse bookmarks data
        bmarks = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA)

        # Generate bookmarks for deployment
        returned = chromium_logger.deploy_bookmarks(bmarks)
        self.assertEqual(
            json.dumps(DEPLOY_BOOKMARKS_DATA, sort_keys=True),
            json.dumps(returned, sort_keys=True),
        )

    def test_07_preferences_monitoring(self):
        # Helper method to write prefs and simulate file modified notification
        def write_prefs(clogger, prefs, path):
            # Write a new supported setting to the preferences file 1
            with open(path, "w") as fd:
                fd.write(json.dumps(prefs, sort_keys=True))
                fd.close()
            # Simulate a change in preferences file 1
            clogger._preferences_file_updated(
                clogger.file_monitors[path],
                Gio.File.new_for_path(path),
                None,
                Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            )

        # Setup test directory
        TMPDIR = self.setup_test_directory(["Profile 1"])

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        prefs1 = DEFAULT_PREFERENCES_1_DATA
        prefs1_path = os.path.join(TMPDIR, "Profile 1/Preferences")

        # Write a new supported setting to the preferences file 1
        prefs1["bookmark_bar"] = {"show_on_all_tabs": True}

        write_prefs(chromium_logger, prefs1, prefs1_path)
        data = mgr.pop()
        received = json.dumps([data[0], json.loads(data[1])], sort_keys=True)

        self.assertEqual(
            json.dumps(
                [
                    chromium_logger.namespace,
                    {"key": "BookmarkBarEnabled", "value": True},
                ],
                sort_keys=True,
            ),
            received,
        )

        # Write an unsupported setting to the preferences file 1
        prefs1["nonexistent"] = {"unknownkey": True}
        write_prefs(chromium_logger, prefs1, prefs1_path)
        self.assertEqual(len(mgr.log), 0)

        # Modify a supported setting on the preferences file 1
        prefs1["browser"] = {"show_home_button": False}
        write_prefs(chromium_logger, prefs1, prefs1_path)
        data = mgr.pop()
        received = json.dumps([data[0], json.loads(data[1])], sort_keys=True)
        self.assertEqual(
            json.dumps(
                [chromium_logger.namespace, {"key": "ShowHomeButton", "value": False}],
                sort_keys=True,
            ),
            received,
        )

        # Modify an unsupported setting on the preferences file 1
        prefs1["nonexistent"] = {"unknownkey": False}
        write_prefs(chromium_logger, prefs1, prefs1_path)
        self.assertEqual(len(mgr.log), 0)

    def test_08_bookmarks_monitoring(self):
        # Helper method to write bookmarks and simulate a file modified notification
        def write_bmarks(clogger, bmarks, path):
            # Write a new supported setting to the preferences file 1
            with open(path, "w") as fd:
                fd.write(json.dumps(bmarks, sort_keys=True))
                fd.close()
            # Simulate a change in preferences file 1
            clogger._bookmarks_file_updated(
                clogger.file_monitors[path],
                Gio.File.new_for_path(path),
                None,
                Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            )

        # Setup test directory
        TMPDIR = self.setup_test_directory(["Profile 1", "Profile 2"])

        bmarks1_path = os.path.join(TMPDIR, "Profile 1/Bookmarks")
        bmarks2_path = os.path.join(TMPDIR, "Profile 2/Bookmarks")

        mgr = MockConnectionManager()
        chromium_logger = FleetCommander.ChromiumLogger(mgr, TMPDIR)

        # Check bookmarks modification for only one session
        write_bmarks(chromium_logger, MODIFIED_BOOKMARKS_DATA, bmarks1_path)

        data = mgr.pop()
        received = json.dumps([data[0], json.loads(data[1])], sort_keys=True)
        print(
            (
                "EXPECTED: %s"
                % json.dumps(
                    [
                        chromium_logger.namespace,
                        {
                            "key": "ManagedBookmarks",
                            "value": DEPLOY_DIFF_BOOKMARKS_DATA,
                        },
                    ],
                    sort_keys=True,
                )
            )
        )
        print(("RECEIVED: %s" % received))

        self.assertEqual(
            json.dumps(
                [
                    chromium_logger.namespace,
                    {"key": "ManagedBookmarks", "value": DEPLOY_DIFF_BOOKMARKS_DATA},
                ],
                sort_keys=True,
            ),
            received,
        )

        # Test bookmarks modification for a second session
        write_bmarks(chromium_logger, MODIFIED_BOOKMARKS_DATA, bmarks2_path)
        data = mgr.pop()
        received = json.dumps([data[0], json.loads(data[1])], sort_keys=True)
        multisession = DEPLOY_DIFF_BOOKMARKS_DATA + DEPLOY_DIFF_BOOKMARKS_DATA
        self.assertEqual(
            json.dumps(
                [
                    chromium_logger.namespace,
                    {"key": "ManagedBookmarks", "value": multisession},
                ],
                sort_keys=True,
            ),
            received,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
