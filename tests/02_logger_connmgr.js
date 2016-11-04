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

function readFile(filename) {
    let input_file = Gio.file_new_for_path(filename);
    let size = input_file.query_info(
        "standard::size",
        Gio.FileQueryInfoFlags.NONE,
        null).get_size();
    let stream = input_file.open_readwrite(null).get_input_stream();
    let data = stream.read_bytes(size, null).get_data();
    stream.close(null);
    return data;
}

// Test suite //

function testSpicePortManagerSubmitChange () {
  // Get temporary file
  let TMPFILE = Gio.file_new_tmp('fc_logger_spiceport_XXXXXX');
  let path = TMPFILE[0].get_path();
  let mgr = new FleetCommander.SpicePortManager(path);
  let PAYLOAD = '["PAYLOAD"]';
  var expectedData = '{"ns":"org.gnome.gsettings","data":"[\\"PAYLOAD\\"]"}'
  mgr.submit_change("org.gnome.gsettings", PAYLOAD);

  // Check change is in queue
  JsUnit.assertEquals(mgr.queue.length, 1);
  JsUnit.assertEquals(mgr.queue[0].ns, "org.gnome.gsettings");
  JsUnit.assertEquals(mgr.queue[0].data, PAYLOAD);

  // Clean queue and quit
  mgr.give_up();
  JsUnit.assertEquals(mgr.queue.length, 0);
  JsUnit.assertEquals(mgr.timeout, 0);

  // Check data has been written to spiceport file
  var data = String(readFile(path));
  JsUnit.assertEquals(expectedData, data);
}

function testSpicePortManagerQueue () {
  // Get temporary file
  let TMPFILE = Gio.file_new_tmp('fc_logger_spiceport_XXXXXX');
  let path = TMPFILE[0].get_path();

  let mgr = new FleetCommander.SpicePortManager(path);
  let PAYLOADS = ['1', '2', '3', '4', '5'];
  var expectedData = '';

  for(let i=0; i<PAYLOADS.length; i++) {
    mgr.submit_change("org.gnome.gsettings", PAYLOADS[i]);
    expectedData += '{"ns":"org.gnome.gsettings","data":"' + PAYLOADS[i] + '"}'
  }

  JsUnit.assertEquals(PAYLOADS.length, mgr.queue.length);
  for(let i=0; i<mgr.queue.length; i++) {
    JsUnit.assertEquals(mgr.queue[i].ns, "org.gnome.gsettings");
    JsUnit.assertEquals(mgr.queue[i].data, PAYLOADS[i]);
  }

  // Clean queue and quit
  mgr.give_up();
  JsUnit.assertEquals(mgr.queue.length, 0);
  JsUnit.assertEquals(mgr.timeout, 0);

  // Check data has been written to spiceport file
  var data = String(readFile(path));
  JsUnit.assertEquals(expectedData, data);
}

JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
