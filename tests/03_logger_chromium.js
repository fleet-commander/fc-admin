#!/usr/bin/gjs
/*
 * Copyright (c) 2015 Red Hat, Inc.
 *
 * GNOME Maps is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * GNOME Maps is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with GNOME Maps; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Authors: Alberto Ruiz <aruiz@redhat.com>
 *          Oliver Gutiérrez <ogutierrez@redhat.com>
 */

const GLib           = imports.gi.GLib;
const Gio            = imports.gi.Gio;
const JsUnit         = imports.jsUnit;
const FleetCommander = imports.fleet_commander_logger;
FleetCommander._debug = true;

var DEFAULT_LOCAL_STATE_DATA = {
    profile: {
        last_active_profiles: []
    }
};

var DEFAULT_PREFERENCES_1_DATA = {
    "browser": {
        "show_home_button": true
    }
};

var DEFAULT_PREFERENCES_2_DATA = {
    "bookmark_bar": {
        "show_on_all_tabs": false
    }
};

var DEFAULT_BOOKMARKS_DATA = {
    "checksum": "ae57f822164f733ef76bee6623fe154b",
    "roots": {
       "bookmark_bar": {
          "children": [ {
             "children": [ {
                "date_added": "13162413694565917",
                "id": "8",
                "meta_info": {
                   "last_visited_desktop": "13162413694567018"
                },
                "name": "Get Fedora",
                "type": "url",
                "url": "https://getfedora.org/"
             }, {
                "date_added": "13162411883407407",
                "id": "5",
                "meta_info": {
                   "last_visited_desktop": "13162411883410030"
                },
                "name": "Fedora Project",
                "type": "url",
                "url": "https://start.fedoraproject.org/"
             } ],
             "date_added": "13162413709642660",
             "date_modified": "13162413767671305",
             "id": "9",
             "name": "Fedora",
             "type": "folder"
          }, {
             "date_added": "13162413767671305",
             "id": "10",
             "meta_info": {
                "last_visited_desktop": "13162413767671448"
             },
             "name": "The Chromium Projects",
             "type": "url",
             "url": "https://www.chromium.org/"
          }, {
             "date_added": "13162413825990580",
             "id": "11",
             "meta_info": {
                "last_visited_desktop": "13162413825992055"
             },
             "name": "Fleet Commander",
             "type": "url",
             "url": "http://fleet-commander.org/"
          } ],
          "date_added": "13162411874534262",
          "date_modified": "13162413825990580",
          "id": "1",
          "name": "Bookmarks bar",
          "type": "folder"
       },
       "other": {
          "children": [{
             "date_added": "13162413694565917",
             "id": "12",
             "meta_info": {
                "last_visited_desktop": "13162413694567018"
             },
             "name": "Fleet Commander Github",
             "type": "url",
             "url": "https://github.com/fleet-commander/"
          }  ],
          "date_added": "13162411874534270",
          "date_modified": "0",
          "id": "2",
          "name": "Other bookmarks",
          "type": "folder"
       },
       "synced": {
          "children": [  ],
          "date_added": "13162411874534271",
          "date_modified": "0",
          "id": "3",
          "name": "Mobile bookmarks",
          "type": "folder"
       }
    },
    "version": 1
}

var MODIFIED_BOOKMARKS_DATA = {
    "checksum": "ae57f822164f733ef76bee6623fe154b",
    "roots": {
       "bookmark_bar": {
          "children": [ {
             "children": [ {
                "date_added": "13162413694565917",
                "id": "8",
                "meta_info": {
                   "last_visited_desktop": "13162413694567018"
                },
                "name": "Get Fedora NOW!!!",
                "type": "url",
                "url": "https://getfedora.org/"
             }, {
                "date_added": "13162411883407407",
                "id": "5",
                "meta_info": {
                   "last_visited_desktop": "13162411883410030"
                },
                "name": "Fedora Project",
                "type": "url",
                "url": "https://start.fedoraproject.org/"
            }, {
                "date_added": "13162413767671305",
                "id": "10",
                "meta_info": {
                  "last_visited_desktop": "13162413767671448"
                },
                "name": "The Chromium Projects",
                "type": "url",
                "url": "https://www.chromium.org/"
            }, {
                "date_added": "13162413767671305",
                "id": "14",
                "meta_info": {
                  "last_visited_desktop": "13162413767671448"
                },
                "name": "SSSD",
                "type": "url",
                "url": "pagure.org/SSSD"
            }],
             "date_added": "13162413709642660",
             "date_modified": "13162413767671305",
             "id": "9",
             "name": "Fedora",
             "type": "folder"
          }, {
             "date_added": "13162413825990580",
             "id": "11",
             "meta_info": {
                "last_visited_desktop": "13162413825992055"
             },
             "name": "Fleet Commander Docs",
             "type": "url",
             "url": "http://fleet-commander.org/documentation.html"
         }, {
            "date_added": "13162413825990580",
            "id": "13",
            "meta_info": {
               "last_visited_desktop": "13162413825992055"
            },
            "name": "FreeIPA",
            "type": "url",
            "url": "http://freeipa.org"
         }],
          "date_added": "13162411874534262",
          "date_modified": "13162413825990580",
          "id": "1",
          "name": "Bookmarks bar",
          "type": "folder"
       },
       "other": {
          "children": [{
             "date_added": "13162413694565917",
             "id": "12",
             "meta_info": {
                "last_visited_desktop": "13162413694567018"
             },
             "name": "Fleet Commander Github",
             "type": "url",
             "url": "https://github.com/fleet-commander/"
          }  ],
          "date_added": "13162411874534270",
          "date_modified": "0",
          "id": "2",
          "name": "Other bookmarks",
          "type": "folder"
       },
       "synced": {
          "children": [  ],
          "date_added": "13162411874534271",
          "date_modified": "0",
          "id": "3",
          "name": "Mobile bookmarks",
          "type": "folder"
       }
    },
    "version": 1
}

var PARSED_BOOKMARKS_DATA = [
    JSON.stringify([["Bookmarks bar", "Fedora"], "8", "https://getfedora.org/", "Get Fedora"]),
    JSON.stringify([["Bookmarks bar", "Fedora"], "5", "https://start.fedoraproject.org/", "Fedora Project"]),
    JSON.stringify([["Bookmarks bar"], "10", "https://www.chromium.org/", "The Chromium Projects"]),
    JSON.stringify([["Bookmarks bar"], "11", "http://fleet-commander.org/", "Fleet Commander"]),
    JSON.stringify([["Other bookmarks"], "12", "https://github.com/fleet-commander/", "Fleet Commander Github"])
]

var DIFFERENCE_BOOKMARKS_DATA = [
    JSON.stringify([["Bookmarks bar","Fedora"], "8", "https://getfedora.org/", "Get Fedora NOW!!!"]),
    JSON.stringify([["Bookmarks bar","Fedora"], "10", "https://www.chromium.org/", "The Chromium Projects"]),
    JSON.stringify([["Bookmarks bar","Fedora"], "14", "pagure.org/SSSD", "SSSD"]),
    JSON.stringify([["Bookmarks bar"], "11", "http://fleet-commander.org/documentation.html", "Fleet Commander Docs"]),
    JSON.stringify([["Bookmarks bar"], "13", "http://freeipa.org", "FreeIPA"]),
]

var MERGED_BOOKMARKS_DATA = [
    JSON.stringify([["Bookmarks bar","Fedora"], "8", "https://getfedora.org/", "Get Fedora NOW!!!"]),
    JSON.stringify([["Bookmarks bar","Fedora"], "5", "https://start.fedoraproject.org/", "Fedora Project"]),
    JSON.stringify([["Bookmarks bar","Fedora"], "10", "https://www.chromium.org/", "The Chromium Projects"]),
    JSON.stringify([["Bookmarks bar","Fedora"], "14", "pagure.org/SSSD", "SSSD"]),
    JSON.stringify([["Bookmarks bar"], "11", "http://fleet-commander.org/documentation.html", "Fleet Commander Docs"]),
    JSON.stringify([["Bookmarks bar"], "13", "http://freeipa.org", "FreeIPA"]),
    JSON.stringify([["Other bookmarks"], "12", "https://github.com/fleet-commander/", "Fleet Commander Github"])
]

var DEPLOY_BOOKMARKS_DATA = [
    {"name": "Fedora", "children": [
        {"name": "Get Fedora", "url": "https://getfedora.org/"},
        {"name": "Fedora Project", "url": "https://start.fedoraproject.org/"}
        ]
    },
    {"name": "The Chromium Projects", "url": "https://www.chromium.org/"},
    {"name": "Fleet Commander", "url": "http://fleet-commander.org/"},
    {"name": "Fleet Commander Github", "url": "https://github.com/fleet-commander/"}
];

DEPLOY_DIFF_BOOKMARKS_DATA = [
    {"name":"Fedora","children": [
        {"name":"Get Fedora NOW!!!","url":"https://getfedora.org/"},
        {"name":"Fedora Project","url":"https://start.fedoraproject.org/"},
        {"name":"The Chromium Projects","url":"https://www.chromium.org/"},
        {"name":"SSSD","url":"pagure.org/SSSD"}
        ]
    },
    {"name":"Fleet Commander Docs","url":"http://fleet-commander.org/documentation.html"},
    {"name":"FreeIPA","url":"http://freeipa.org"},{"name":"Fleet Commander Github","url":"https://github.com/fleet-commander/"}
]

function setup_test_directory(sessions, p1_prefs, p2_prefs) {
    var sessions = sessions || [];
    var profile1_prefs = p1_prefs || DEFAULT_PREFERENCES_1_DATA;
    var profile2_prefs = p2_prefs || DEFAULT_PREFERENCES_2_DATA;
    // Create a temporary directory for testing
    let TMPDIR = GLib.dir_make_tmp('fc_logger_chromium_XXXXXX')
    // Create profile directories
    JsUnit.assertEquals(0,
        GLib.mkdir_with_parents(TMPDIR + '/Profile 1/', 0o755));
    JsUnit.assertEquals(0,
        GLib.mkdir_with_parents(TMPDIR + '/Profile 2/', 0o755));
    // Create local state file
    let local_state_data = DEFAULT_LOCAL_STATE_DATA;
    local_state_data['profile']['last_active_profiles'] = sessions;
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Local State',
            JSON.stringify(local_state_data)));
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Profile 1/Preferences',
            JSON.stringify(profile1_prefs)));
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Profile 2/Preferences',
            JSON.stringify(profile2_prefs)));
    // Bookmarks data
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Profile 1/Bookmarks',
            JSON.stringify(DEFAULT_BOOKMARKS_DATA)));
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Profile 2/Bookmarks',
            JSON.stringify(DEFAULT_BOOKMARKS_DATA)));

    return TMPDIR;
}

/* Mock objects */

var MockConnectionManager = function () {
  this.log = [];
}

MockConnectionManager.prototype.submit_change = function (namespace, data) {
  this.log.push([namespace, data]);
}

MockConnectionManager.prototype.pop = function () {
  return this.log.pop();
}


// Test suite //

function testLocalStateStartup () {
    // Setup test directory
    var TMPDIR = setup_test_directory(
        ['Profile 1'],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    JsUnit.assertTrue(
        TMPDIR + '/Profile 1/Preferences' in chromium_logger.monitored_preferences);
}

function testLocalStateMonitoring () {

    // Helper method to simulate file modified notification
    this.simulate_filenotification = function(clogger) {
        clogger._local_state_file_updated(
            clogger.file_monitors[clogger.local_state_path],
            Gio.File.new_for_path(clogger.local_state_path),
            null,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT);
    }

    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    // Add a new session to the Local State file
    let local_state_data = DEFAULT_LOCAL_STATE_DATA;
    local_state_data['profile']['last_active_profiles'] = ['Profile 1'];
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Local State',
            JSON.stringify(local_state_data)));
    // Simulate a local state file modification
    this.simulate_filenotification(chromium_logger);
    JsUnit.assertTrue(
        TMPDIR + '/Profile 1/Preferences' in chromium_logger.monitored_preferences);


    // Add a new session to the Local State file
    local_state_data['profile']['last_active_profiles'] = ['Profile 1', 'Profile 2'];
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Local State',
            JSON.stringify(local_state_data)));
    // Simulate a local state file modification
    this.simulate_filenotification(chromium_logger);

    JsUnit.assertTrue(
        TMPDIR + '/Profile 2/Preferences' in chromium_logger.monitored_preferences);
}

function testGetPreferenceValue () {
    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    // Existent key
    JsUnit.assertEquals(
        true,
        chromium_logger.get_preference_value(
            DEFAULT_PREFERENCES_1_DATA,
            'browser.show_home_button'));

    // Non existent key
    JsUnit.assertEquals(
        null,
        chromium_logger.get_preference_value(
            DEFAULT_PREFERENCES_1_DATA,
            'nonexistent.key.name'));
}

function testPreferencesMonitoring () {

    // Helper method to write prefs and simulate file modified notification
    this.write_prefs = function(clogger, prefs, path) {
        // Write a new supported setting to the preferences file 1
        JsUnit.assertTrue(
            GLib.file_set_contents(path,
                JSON.stringify(prefs)));
        // Simulate a change in preferences file 1
        clogger._preferences_file_updated(
            clogger.file_monitors[path],
            Gio.File.new_for_path(path),
            null,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT);
    }

    // Setup test directory
    var TMPDIR = setup_test_directory(
        ['Profile 1', 'Profile 2'],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    var prefs1 = DEFAULT_PREFERENCES_1_DATA;
    var prefs1_path = TMPDIR + '/Profile 1/Preferences'

    // Write a new supported setting to the preferences file 1
    prefs1['bookmark_bar'] = {'show_on_all_tabs': true };
    this.write_prefs(chromium_logger, prefs1, prefs1_path);
    var data = mgr.pop()
    var received = JSON.stringify([data[0], JSON.parse(data[1])]);
    JsUnit.assertEquals(
        JSON.stringify([chromium_logger.namespace,
            { key: 'BookmarkBarEnabled', value: true }]),
        received);

    // Write an unsupported setting to the preferences file 1
    prefs1['nonexistent'] = {'unknownkey': true };
    this.write_prefs(chromium_logger, prefs1, prefs1_path);
    JsUnit.assertEquals(undefined, mgr.pop());

    // Modify a supported setting on the preferences file 1
    prefs1['browser'] = {'show_home_button': false };
    this.write_prefs(chromium_logger, prefs1, prefs1_path);
    var data = mgr.pop()
    var received = JSON.stringify([data[0], JSON.parse(data[1])]);
    JsUnit.assertEquals(
        JSON.stringify([chromium_logger.namespace,
            { key: 'ShowHomeButton', value: false }]),
        received);

    // Modify an unsupported setting on the preferences file 1
    prefs1['nonexistent'] = {'unknownkey': false };
    this.write_prefs(chromium_logger, prefs1, prefs1_path);
    JsUnit.assertEquals(undefined, mgr.pop());
}

function testBookmarksParse () {
    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    // Check bookmarks tree parsing to policy format
    let result = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA);
    JsUnit.assertEquals(
        JSON.stringify(PARSED_BOOKMARKS_DATA),
        JSON.stringify(result));
}

function testGetModifiedBookmarks () {
    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    // Parse bookmarks data
    let bmarks1 = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA);
    let bmarks2 = chromium_logger.parse_bookmarks(MODIFIED_BOOKMARKS_DATA);

    // Check difference with same bookmarks is an empty list
    let returned = chromium_logger.get_modified_bookmarks(bmarks1, bmarks1);
    JsUnit.assertEquals(
        JSON.stringify([]),
        JSON.stringify(returned));

    // Check difference with different bookmarks data is ok
    returned = chromium_logger.get_modified_bookmarks(bmarks1, bmarks2);
    JsUnit.assertEquals(
        JSON.stringify(DIFFERENCE_BOOKMARKS_DATA),
        JSON.stringify(returned));

}

function testDeployBookmarks () {
    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);
    // Parse bookmarks data
    let bmarks = chromium_logger.parse_bookmarks(DEFAULT_BOOKMARKS_DATA);

    // Generate bookmarks for deployment
    let returned = chromium_logger.deploy_bookmarks(bmarks);
    JsUnit.assertEquals(
        JSON.stringify(DEPLOY_BOOKMARKS_DATA),
        JSON.stringify(returned));
}

function testBookmarksMonitoring () {

    // Helper method to write bookmarks and simulate a file modified notification
    this.write_bmarks = function(clogger, bmarks, path) {
        // Write a new supported setting to the preferences file 1
        JsUnit.assertTrue(
            GLib.file_set_contents(path,
                JSON.stringify(bmarks)));
        // Simulate a change in preferences file 1
        clogger._bookmarks_file_updated(
            clogger.file_monitors[path],
            Gio.File.new_for_path(path),
            null,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT);
    }

    // Setup test directory
    var TMPDIR = setup_test_directory(
        [],
        null,
        null
    );

    let bmarks1_path = TMPDIR + '/Profile 1/Bookmarks';
    let bmarks2_path = TMPDIR + '/Profile 2/Bookmarks';
    let mgr = new MockConnectionManager();
    let chromium_logger = new FleetCommander.ChromiumLogger(mgr, TMPDIR);

    // Check bookmarks modification for only one session
    this.write_bmarks(chromium_logger, MODIFIED_BOOKMARKS_DATA, bmarks1_path);
    let data = mgr.pop()
    let received = JSON.stringify([data[0], JSON.parse(data[1])]);
    JsUnit.assertEquals(
        JSON.stringify([chromium_logger.namespace,
            { key: 'ManagedBookmarks', value: DEPLOY_DIFF_BOOKMARKS_DATA}]),
        received);

    // Test bookmarks modification for a second session
    this.write_bmarks(chromium_logger, MODIFIED_BOOKMARKS_DATA, bmarks2_path);
    data = mgr.pop()
    received = JSON.stringify([data[0], JSON.parse(data[1])]);
    let multisession = DEPLOY_DIFF_BOOKMARKS_DATA.slice();
    Array.prototype.push.apply(multisession, DEPLOY_DIFF_BOOKMARKS_DATA);
    JsUnit.assertEquals(
        JSON.stringify([chromium_logger.namespace,
            { key: 'ManagedBookmarks', value: multisession}]),
        received);
}

JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
