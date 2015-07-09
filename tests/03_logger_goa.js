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
const System         = imports.system;
const FleetCommander = imports.fleet_commander_logger;
//FleetCommander._debug = true;

// Mock objects //

var MockConnectionManager = function (counter) {
  this.log = [];
  this.counter = counter;
}
MockConnectionManager.prototype.submit_change = function (namespace, data) {
  this.log.push([namespace, data]);
}
MockConnectionManager.prototype.finish_changes = function () {
}
MockConnectionManager.prototype.pop = function () {
  return this.log.pop();
}

MockFileMonitor = function (path, callback) {
  this.path = path;
  this.callback = callback;
}
MockFileMonitor.prototype.emit = function (event_type) {
  this.callback (this, null, null, event_type);
}

// We replace the file monitor implementation
FleetCommander.FileMonitor = MockFileMonitor;

// Setup environment //
let xdgconfig = null;
try {
  xdgconfig = GLib.dir_make_tmp("fcmdr-XXXXXX");
} catch (e) {
  printerr ("Could not create temporary directory");
  System.exit(1);
}

let goadir = xdgconfig + "/goa-1.0";
if (GLib.mkdir_with_parents (goadir, parseInt("755", 8)) == -1) {
  printerr ("Could not create " + goadir);
  System.exit(1);
}
GLib.setenv ('XDG_CONFIG_HOME', xdgconfig, true);

function writeAccountContent (content) {
  let accounts = goadir+"/accounts.conf"
  let ret = false;
  try {
    ret = GLib.file_set_contents (accounts, content);
  } catch (e) {}
  JsUnit.assertTrue("Could not set contents to "+accounts, ret);
}

// Test suite //

function testGoaEmpty () {
  let server = new MockConnectionManager (2);
  let goa = new FleetCommander.GoaLogger(server);
  let change = server.pop();
  JsUnit.assertNotNull (change);
  JsUnit.assertEquals(change[0], "org.gnome.online-accounts");
  JsUnit.assertEquals(change[1], "{}");
}

function testGoeExisting () {
  let server = new MockConnectionManager (2);

  let content = "[Account account_1234567890_0]\n" +
  "Provider=google\n" +
  "Identity=someone@gmail.com";
  writeAccountContent(content);

  let goa = new FleetCommander.GoaLogger(server);
  let change = server.pop();

  JsUnit.assertNotNull (change);
  JsUnit.assertEquals(change[0], "org.gnome.online-accounts");
  JsUnit.assertEquals(JSON.stringify(JSON.parse(change[1])),
                      JSON.stringify({
    "fcmdr_account_1234567890_0": {
      "Provider": "google",
      "Identity": "someone@gmail.com",
    },
  }));
}

function testGoaFileChanged () {
  let server = new MockConnectionManager (2);
  let goa = new FleetCommander.GoaLogger(server);

  let content = "[Account account_1234567890_0]\n" +
    "Provider=google\n" +
  "Identity=someone@gmail.com";
  writeAccountContent(content);

  goa.monitor.emit(Gio.FileMonitorEvent.CHANGED);

  let change = server.pop();
  JsUnit.assertEquals("org.gnome.online-accounts", change[0]);
  JsUnit.assertEquals(JSON.stringify(JSON.parse(change[1])),
                      JSON.stringify({
    'fcmdr_account_1234567890_0': {
      "Provider":"google", "Identity":"someone@gmail.com"
    },
  }));
}

function testGoaFileRemoved () {
  let server = new MockConnectionManager (2);

  let content = "[Account account_1234567890_0]\n" +
  "Provider=google\n" +
  "Identity=someone@gmail.com";
  writeAccountContent(content);

  let goa = new FleetCommander.GoaLogger(server);
  GLib.unlink (goadir + "/accounts.conf");
  goa.monitor.emit(Gio.FileMonitorEvent.DELETED);

  let change = server.pop();
  JsUnit.assertNotNull(change);
  JsUnit.assertEquals(change[0], "org.gnome.online-accounts");
  JsUnit.assertEquals(change[1], "{}");
}

function testGoaUnparseable () {
  let server = new MockConnectionManager (2);

  let content = "{}%{$%#}%$}{%$}{";
  writeAccountContent(content);

  let goa = new FleetCommander.GoaLogger(server);
  let change = server.pop();
  JsUnit.assertNotNull(change);
  JsUnit.assertEquals(change[0], "org.gnome.online-accounts");
  JsUnit.assertEquals(change[1], "{}");
}

function testGoaBadSectionIgnored () {
  let server = new MockConnectionManager (2);
  let content = "[RamdonSection Foo]\nsomekey=1";
  writeAccountContent(content);

  let goa = new FleetCommander.GoaLogger(server);
  let change = server.pop();
  JsUnit.assertNotNull(change);
  JsUnit.assertEquals(change[0], "org.gnome.online-accounts");
  JsUnit.assertEquals(change[1], "{}");
}

//TODO: Add no provider/no identity test

// Run test suite //

let ret = JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);

// Cleanup and return
GLib.unlink (goadir + "/accounts.conf");
GLib.rmdir (goadir);
GLib.rmdir (xdgconfig);

ret; // Last value in the script becomes return code
