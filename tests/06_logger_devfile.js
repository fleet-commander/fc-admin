#!/usr/bin/gjs
/*
 * Copyright (c) 2015 Red Hat, Inc.
 *
 * Fleet Commander is free software; you can redistribute it and/or modify
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
 *          Matthew Barnes <mbarnes@redhat.com>
 */

const GLib           = imports.gi.GLib;
const Gio            = imports.gi.Gio;
const JsUnit         = imports.jsUnit;
const FleetCommander = imports.fleet_commander_logger;

function testParseOptions () {
  FleetCommander.DEV_PATH = "/tmp";
  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 8181);
  JsUnit.assertEquals (options['admin_server_host'], 'localhost');

  FleetCommander.DEV_PATH = "/dev/"
}

function testParseDevfileNone () {
  FleetCommander.DEV_PATH = GLib.dir_make_tmp ("fcmdr-XXXXXX") + "/";

  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 8181);
  JsUnit.assertEquals (options['admin_server_host'], 'localhost'); 

  GLib.rmdir (FleetCommander.DEV_PATH);
  FleetCommander.DEV_PATH = "/dev/"
}

function testParseDevfileHost () {
  FleetCommander.DEV_PATH = GLib.dir_make_tmp ("fcmdr-XXXXXX") + "/";

  let somehost = FleetCommander.DEV_PATH + "fleet-commander_somehost.com-9009";
  GLib.file_set_contents (somehost, "", -1);

  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 9009);
  JsUnit.assertEquals (options['admin_server_host'], 'somehost.com'); 

  GLib.unlink (somehost);
  GLib.rmdir (FleetCommander.DEV_PATH);
  FleetCommander.DEV_PATH = "/dev/"
}

function testParseDevfileIP () {
  FleetCommander.DEV_PATH = GLib.dir_make_tmp ("fcmdr-XXXXXX") + "/";

  let somehost = FleetCommander.DEV_PATH + "fleet-commander_192.168.1.1-9009";
  GLib.file_set_contents (somehost, "", -1);

  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 9009);
  JsUnit.assertEquals (options['admin_server_host'], '192.168.1.1'); 

  GLib.unlink (somehost);
  GLib.rmdir (FleetCommander.DEV_PATH);
  FleetCommander.DEV_PATH = "/dev/"
}

function testParseDevfileLocalhost () {
  FleetCommander.DEV_PATH = GLib.dir_make_tmp ("fcmdr-XXXXXX") + "/";

  let somehost = FleetCommander.DEV_PATH + "fleet-commander_localhost-9009";
  GLib.file_set_contents (somehost, "", -1);

  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 9009);
  //This value is taken from the ip mocked tool in tests/tools/ip
  JsUnit.assertEquals (options['admin_server_host'], '192.168.0.1');

  GLib.unlink (somehost);
  GLib.rmdir (FleetCommander.DEV_PATH);
  FleetCommander.DEV_PATH = "/dev/"
}

function testParseDevfile127_0_0_1 () {
  FleetCommander.DEV_PATH = GLib.dir_make_tmp ("fcmdr-XXXXXX") + "/";

  let somehost = FleetCommander.DEV_PATH + "fleet-commander_127.0.0.1-9009";
  GLib.file_set_contents (somehost, "", -1);

  var options = FleetCommander.parse_options();
  options = FleetCommander.get_options_from_devfile (options);

  JsUnit.assertEquals (options['admin_server_port'], 9009);
  //This value is taken from the ip mocked tool in tests/tools/ip
  JsUnit.assertEquals (options['admin_server_host'], '192.168.0.1');

  GLib.unlink (somehost);
  GLib.rmdir (FleetCommander.DEV_PATH);
  FleetCommander.DEV_PATH = "/dev/"
}

JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
