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
}
MockConnectionManager.prototype.submit_change = function (namespace, data) {
  this.log.push([namespace, data]);
}
MockConnectionManager.prototype.finish_changes = function () {
}
MockConnectionManager.prototype.pop = function () {
  return this.log.pop();
}

// NMClient Mock
let NMClientMock = function (dbusconn) {
}

NMClientMock.prototype.connect = function (s, f) {
    this.handler = f;
}

NMClientMock.prototype.emit_connection_added = function (conn) {
    this.handler (this, conn);
}

// NMConnection Mock
let NMConnectionMock = function (type, settings, secrets) {
    this.type = type;
    this.settings = settings;
    this.secrets = secrets;
}

NMConnectionMock.prototype.to_dbus = function (flag) {
    return new GLib.Variant ('a{sa{ss}}', this.settings);
}

NMConnectionMock.prototype.get_connection_type = function () {
    return this.type;
}
NMConnectionMock.prototype.get_secrets = function (setting, cancellable) {
    return new GLib.Variant ('a{sa{ss}}', this.secrets);
}

FleetCommander.NM = {
    Client: { 'new': function (dbusconn) { return new NMClientMock(dbusconn); }},
    ConnectionSerializationFlags: {
        ALL: 1,
    },
};

function setupNetworkConnection (type, settings, secrets) {
    let loop = GLib.MainLoop.new (null, false);
    let connmgr = new MockConnectionManager ();

    let nmlogger = new FleetCommander.NMLogger (connmgr);

    let conn = new NMConnectionMock (type, settings, secrets);

    /* We wait for the logger to catch the bus name */
    GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, function () {
        this.nmclient.emit_connection_added (conn);
        loop.quit();
    }.bind(nmlogger));

    GLib.timeout_add(GLib.PRIORITY_DEFAULT_IDLE, 3000, function () {
        loop.quit();
        return false;
    });
    loop.run ();

    return connmgr;
}

// Test suite //
function testNMVpn () {
    let connmgr = setupNetworkConnection ("vpn", {vpn: {user: "foo", passwd: ""}}, {vpn: {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    JsUnit.assertEquals (item[1], JSON.stringify ({vpn: {user: "foo", passwd: "asd"}}));
}

function testNMEthernet () {
    let connmgr = setupNetworkConnection ("802-3-ethernet", {"802-1x": {user: "foo", passwd: ""}}, {"802-1x": {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    JsUnit.assertEquals (item[1], JSON.stringify ({"802-1x": {user: "foo", passwd: "asd"}}));
}

function testNMWifi () {
    let connmgr = setupNetworkConnection ("802-11-wireless", {"802-11-wireless-security": {user: "foo", passwd: ""}}, {"802-11-wireless-security": {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    JsUnit.assertEquals (item[1], JSON.stringify ({"802-11-wireless-security": {user: "foo", passwd: "asd"}}));
}

// Run test suite //
JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
