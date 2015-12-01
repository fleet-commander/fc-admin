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
//FleetCommander._debug = true;

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
MockConnectionManager.prototype.finish_changes = function () {
    this.loop.quit();
}

/* Test suite */

function testInhibitor () {
  let inhibitor = new FleetCommander.ScreenSaverInhibitor();
  JsUnit.assertTrue(inhibitor.cookie == 9191);
  inhibitor.uninhibit();
  JsUnit.assertTrue(inhibitor.cookie == null);
}

function setupDbusCall (method, args, glog) {
  let loop = GLib.MainLoop.new (null, false);
  glog.connmgr.loop = loop;

  let proxy = Gio.DBusProxy.new_sync (Gio.DBus.session, Gio.DBusProxyFlags.NONE, null,
                                    glog.BUS_NAME,
                                    glog.OBJECT_PATH,
                                    glog.INTERFACE_NAME,
                                    null);

  /* We wait for the logger to catch the bus name */
  GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, function () {
    if (glog.dconf_subscription_id != 0) {
      this.call_sync(method, args, Gio.DBusCallFlags.NONE, 1000, null);
      return false;
    } else {
      return true;
    }
  }.bind(proxy));

  /* We have a timeout of 3 seconds to wait for the mainloop */
  GLib.timeout_add(GLib.PRIORITY_DEFAULT_IDLE, 3000, function () {
    loop.quit();
    return false;
  }.bind(proxy));

  loop.run();
}

function testGSettingsLoggerWriteKeyForKnownSchema () {
  let mgr  = new MockConnectionManager();
  let glog = new FleetCommander.GSettingsLogger(mgr);

  let args = GLib.Variant.new ("(ay)", [[]]);
  setupDbusCall ('Change', args, glog);

  let change = mgr.pop();
  JsUnit.assertTrue(change != null);
  JsUnit.assertTrue(change.length == 2);

  JsUnit.assertEquals(change[0], "org.gnome.gsettings");

  // we normalize the json object using the same parser
  JsUnit.assertEquals(JSON.stringify({'key':'/test/test', 'schema':'fleet-commander-test','value':true,'signature':'b'}),
                      JSON.stringify(JSON.parse(change[1])));

  Gio.DBus.get_sync (Gio.BusType.SESSION, null).signal_unsubscribe (glog.dconf_subscription_id);
}

function testGSettingsLoggerWriteKeyForUnknownSchema () {
  let mgr  = new MockConnectionManager();
  let glog = new FleetCommander.GSettingsLogger(mgr);

  setupDbusCall('ChangeCommon', null, glog);

  let change = mgr.pop();

  JsUnit.assertTrue(change == null);

  Gio.DBus.get_sync (Gio.BusType.SESSION, null).signal_unsubscribe (glog.dconf_subscription_id);
}

function testGSettingsLoggerWriteKeyForGuessableSchema () {
  let mgr  = new MockConnectionManager();
  let glog = new FleetCommander.GSettingsLogger(mgr);

  setupDbusCall('ChangeUnique', null, glog);

  let change = mgr.pop();

  JsUnit.assertEquals(change[0], "org.gnome.gsettings");
  JsUnit.assertEquals(JSON.stringify({'key':'/reloc/foo/fc-unique',
                                       'schema':'fleet-commander-reloc1',
                                       'value':true,
                                       'signature':'b'}),
                      JSON.stringify(JSON.parse(change[1])));
  Gio.DBus.get_sync (Gio.BusType.SESSION, null).signal_unsubscribe (glog.dconf_subscription_id);
}

function testGSettingsLoggerGuessSchemaCachedPath () {
  let mgr  = new MockConnectionManager();
  let glog = new FleetCommander.GSettingsLogger(mgr);

  setupDbusCall('ChangeCommon', null, glog);
  setupDbusCall('ChangeUnique', null, glog);
  mgr.pop();
  setupDbusCall('ChangeCommon', null, glog);

  let change = mgr.pop();
  JsUnit.assertEquals(change[0], "org.gnome.gsettings");
  JsUnit.assertEquals(JSON.stringify({'key':'/reloc/foo/fc-common',
                                       'schema':'fleet-commander-reloc1',
                                       'value':true,
                                       'signature':'b'}),
                      JSON.stringify(JSON.parse(change[1])));

  Gio.DBus.get_sync (Gio.BusType.SESSION, null).signal_unsubscribe (glog.dconf_subscription_id);
}


function testLibreOfficeLoggerWriteKey () {
  let mgr  = new MockConnectionManager();
  let glog = new FleetCommander.GSettingsLogger(mgr);

  setupDbusCall ('ChangeLibreOffice', null, glog);

  let change = mgr.pop();

  JsUnit.assertTrue(change != null);
  JsUnit.assertTrue(change.length == 2);

  JsUnit.assertEquals(change[0], "org.libreoffice.registry");

  // we normalize the json object using the same parser
  JsUnit.assertEquals(JSON.stringify({'key':'/org/libreoffice/registry/somepath/somekey', 'value':123,'signature':'i'}),
                      JSON.stringify(JSON.parse(change[1])));

  Gio.DBus.get_sync (Gio.BusType.SESSION, null).signal_unsubscribe (glog.dconf_subscription_id);
}


JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
