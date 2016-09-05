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
const Json           = imports.gi.Json;
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
    return this.settings;
}

NMConnectionMock.prototype.get_connection_type = function () {
    return this.type;
}
NMConnectionMock.prototype.get_secrets = function (setting, cancellable) {
    return this.secrets;
}

FleetCommander.NM = {
    Client: { 'new': function (dbusconn) { return new NMClientMock(dbusconn); }},
    ConnectionSerializationFlags: {
        ALL: 1,
    },
};

function serializeConfigObject (obj) {
    if (!(obj instanceof Object)) {
        return null;
    }

    let dict_top = GLib.VariantBuilder.new (new GLib.VariantType ("a{sa{sv}}"));
    for (let key_top in obj) {
        let dict_sub = GLib.VariantDict.new (new GLib.Variant ("a{sv}", {}));
        if (!(obj[key_top] instanceof Object))
           continue;
        for (let key_sub in obj[key_top]) {
            let item = Json.gvariant_deserialize_data (JSON.stringify (obj[key_top][key_sub]), -1, null);
            dict_sub.insert_value (key_sub, item);
        }
        let entry = GLib.VariantBuilder.new (new GLib.VariantType ("{sa{sv}}"));
        entry.add_value (new GLib.Variant ("s", key_top));
        entry.add_value (dict_sub.end ());

        dict_top.add_value (entry.end ());
    }

    return dict_top.end ();
}

function unmarshallVariant (data) {
    return GLib.Variant.parse (null, data, null, null);
}

function setupNetworkConnection (type, settings, secrets) {
    let loop = GLib.MainLoop.new (null, false);
    let connmgr = new MockConnectionManager ();

    let nmlogger = new FleetCommander.NMLogger (connmgr);

    let conn = new NMConnectionMock (type,
                                     serializeConfigObject(settings),
                                     serializeConfigObject(secrets));

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

function lookupString (variant, path) {
    return lookupValue (variant, path).get_string ()[0];
}

function lookupValue (variant, path) {
    let sub = variant;
    let split = path.split (".");
    for (let i in split) {
        sub = sub.lookup_value (split[i], null);
    }
    return sub;
}

// Test suite //
function testNMVpn () {
    let connmgr = setupNetworkConnection ("vpn", {vpn: {user: "foo", passwd: ""}}, {vpn: {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    let payload = JSON.parse (item[1]);

    let conf = unmarshallVariant (payload.data);
    JsUnit.assertEquals (lookupString (conf, "vpn.user"), "foo");
    JsUnit.assertEquals (lookupString (conf, "vpn.passwd"), "asd");
}

function testNMEthernet () {
    let connmgr = setupNetworkConnection ("802-3-ethernet", {"802-1x": {user: "foo", passwd: ""}}, {"802-1x": {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    let payload = JSON.parse (item[1]);

    let conf = unmarshallVariant (payload.data);
    JsUnit.assertEquals (lookupString (conf, "802-1x.user"), "foo");
    JsUnit.assertEquals (lookupString (conf, "802-1x.passwd"), "asd");
}

function testNMWifi () {
    let connmgr = setupNetworkConnection ("802-11-wireless", {"802-11-wireless-security": {user: "foo", passwd: ""}}, {"802-11-wireless-security": {passwd: "asd"}});
    let item = connmgr.pop ();
    JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
    let payload = JSON.parse (item[1]);

    let conf = unmarshallVariant (payload.data);
    JsUnit.assertEquals (lookupString (conf, "802-11-wireless-security.user"), "foo");
    JsUnit.assertEquals (lookupString (conf, "802-11-wireless-security.passwd"), "asd");
}


function testFilters () {
  let secrets = {
    "802-11-wireless-security": {username: "me", "leap-password": "somepassword"},
    "802-1x": {username: "me", password: "somepassword"},
    vpn: {data: {secrets: {
      username: "asd",
      password: "somepassword",
      'Xauth password': 'somepassword'
    }}}
  };

  //VPN
  let connmgr = setupNetworkConnection ("vpn", {}, secrets);
  let item = connmgr.pop ();
  JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");

  let vpnout = JSON.parse(item[1]);
  JsUnit.assertTrue  (vpnout instanceof Object);
  let vpnconf = unmarshallVariant (vpnout.data);
  JsUnit.assertEquals (lookupValue (vpnconf, "vpn.data.secrets.password"), null);
  JsUnit.assertEquals (lookupValue (vpnconf, "vpn.data.secrets.Xauth password"), null);

  //Ethernet
  connmgr = setupNetworkConnection ("802-3-ethernet", {}, secrets);
  item = connmgr.pop ();

  JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");

  let ethout = JSON.parse(item[1]);
  JsUnit.assertTrue  (ethout instanceof Object);
  let ethconf = unmarshallVariant (ethout.data);
  JsUnit.assert (lookupValue(ethconf, "802-1x.password") == null);

  //Wifi
  connmgr = setupNetworkConnection ("802-11-wireless", {}, secrets);
  item = connmgr.pop ();

  JsUnit.assertEquals (item[0], "org.freedesktop.NetworkManager");
  let wifiout = JSON.parse(item[1]);
  JsUnit.assertTrue  (wifiout instanceof Object);
  let wificonf = unmarshallVariant (wifiout.data);
  JsUnit.assert (lookupValue(wificonf, "802-1x.password") == null);
  JsUnit.assert (lookupValue(wificonf, "802-11-wireless-security.leap-password") == null);
}

// Run test suite //
JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
