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
const Soup           = imports.gi.Soup;
const JsUnit         = imports.jsUnit;
const FleetCommander = imports.fleet_commander_logger;
//FleetCommander._debug = true;

// Mock web server //

var MockWebServer = function (counter) {
  this.HOST = "localhost";
  this.server = new Soup.Server ();
  this.bound = false;
  this.port = 8000;
  this.queue = [];

  // this lets us know how many requests to serve before we quit the mainloop //
  this.counter = counter;

  // we find a port that suits us //
  for (; this.port<9999; this.port++) {
    let addr = Gio.InetSocketAddress.new_from_string (this.HOST, this.port);
    try {
      this.bound = this.server.listen_local (this.port, Soup.ServerListenOptions.IPV4_ONLY);
    } catch (e) { }
    if (this.bound)
      break;
  }
  if (this.bound == false)
    return;

  // 2s timeout on the mainloop
  this.timeout = GLib.timeout_add (GLib.PRIORITY_DEFAULT, 2000, function () {
    this.timeout = 0;
    this.server.disconnect();
    this.loop.quit();
    return false;
  }.bind(this));

  this.server.add_handler (FleetCommander.SUBMIT_PATH, this.submit_change_cb.bind(this));
}

MockWebServer.prototype.submit_change_cb = function (server, msg, path, query, client) {
  msg.set_status (Soup.Status.OK);
  msg.set_response ("application/json", Soup.MemoryUse.COPY, '{"status": "ok"}');

  msg.connect('finished', function () {
    this.queue.push([path, msg]);

    this.counter--;
    if (this.counter > 0)
      return;

    this.server.disconnect();
    this.loop.quit();
  }.bind(this));
}

MockWebServer.prototype.pop = function () {
  return this.queue.pop();
}

// Test suite //

function testConnectionManagerSubmitChange () {
  let PAYLOAD = '["PAYLOAD"]';
  let server = new MockWebServer (1);
  JsUnit.assertTrue(server.bound);
  server.loop = GLib.MainLoop.new (null, false);

  let mgr = new FleetCommander.ConnectionManager(server.HOST, server.port);
  mgr.submit_change ("org.gnome.gsettings", PAYLOAD);

  server.loop.run();
  if (server.timeout != 0) {
    GLib.source_remove (server.timeout);
  }
  JsUnit.assertTrue("Server did not receive any requests", server.timeout != 0);

  let last = server.pop();

  JsUnit.assertNotNull(last);
  JsUnit.assertEquals(last[0], FleetCommander.SUBMIT_PATH + "org.gnome.gsettings");

  JsUnit.assertNotNull(last[1]);

  JsUnit.assertEquals(last[1].method, "POST");

  JsUnit.assertNotNull(last[1].request_headers);
  JsUnit.assertNotNull(last[1].request_headers.get("Content-Type"), "application/json");

  JsUnit.assertNotNull(last[1].request_body.data);

  JsUnit.assertEquals(last[1].request_body.data, PAYLOAD);

  mgr.give_up();
  JsUnit.assertEquals(mgr.queue.length, 0);
  JsUnit.assertEquals(mgr.timeout, 0);
}

function testConnectionManagerQueue () {
  let PAYLOADS = ['1', '2', '3', '4', '5'];
  let server = new MockWebServer (PAYLOADS.length);
  JsUnit.assertTrue(server.bound);

  server.loop = GLib.MainLoop.new (null, false);

  let mgr = new FleetCommander.ConnectionManager(server.HOST, server.port);
  for(let i=0; i<PAYLOADS.length; i++) {
    mgr.submit_change ("org.gnome.gsettings", PAYLOADS[i]);
  }

  JsUnit.assertEquals(PAYLOADS.length, mgr.queue.length);
  for(let i=0; i<mgr.queue.length; i++) {
    JsUnit.assertEquals(mgr.queue[i].ns,   "org.gnome.gsettings");
    JsUnit.assertEquals(mgr.queue[i].data, PAYLOADS[i]);
  }

  server.loop.run();
  if (server.timeout != 0) {
    GLib.source_remove (server.timeout);
  }
  JsUnit.assertTrue("Server did not receive any requests", server.timeout != 0);

  JsUnit.assertEquals(server.queue.length, PAYLOADS.length);
  for(let i=0; i<server.queue.length; i++) {
    JsUnit.assertEquals(server.queue[i][0],   FleetCommander.SUBMIT_PATH + "org.gnome.gsettings");
    JsUnit.assertNotNull(server.queue[i][1].request_body);
    JsUnit.assertNotNull(server.queue[i][1].request_body.data);
    let data = server.queue[i][1].request_body.data;
    JsUnit.assertTrue(PAYLOADS.indexOf(data) != -1);
  }

  mgr.give_up();
}

JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
