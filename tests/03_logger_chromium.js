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
        TMPDIR + '/Profile 1/Preferences' in chromium_logger.monitored_sessions);
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
        TMPDIR + '/Profile 1/Preferences' in chromium_logger.monitored_sessions);


    // Add a new session to the Local State file
    local_state_data['profile']['last_active_profiles'] = ['Profile 1', 'Profile 2'];
    JsUnit.assertTrue(
        GLib.file_set_contents(TMPDIR + '/Local State',
            JSON.stringify(local_state_data)));
    // Simulate a local state file modification
    this.simulate_filenotification(chromium_logger);

    JsUnit.assertTrue(
        TMPDIR + '/Profile 2/Preferences' in chromium_logger.monitored_sessions);
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

JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
