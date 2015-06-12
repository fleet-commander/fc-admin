#!/usr/bin/gjs

/* vim: set et ts=4 sw=4: */
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
 *          Matthew Barnes <mbarnes@redhat.com>
 */


const GLib = imports.gi.GLib;
const Gio  = imports.gi.Gio;
const Soup = imports.gi.Soup;

const ml = new GLib.MainLoop(null, false);
var options = null;
var _debug = false;

function debug (msg) {
  if (!_debug)
      return;
  printerr("DEBUG: " + msg);
}

function parse_options () {
  let result = {
      'admin_server_host': 'localhost',
      'admin_server_port': 8181
  }

  let file = null;

  for(let i = 0; i < ARGV.length; i++) {
    switch(ARGV[i]) {
      case "--help":
      case "-h":
        printerr("--help/-h:               show this output message");
        printerr("--configuration/-c FILE: sets the configuration file");
        printerr("--debug/-d/-v:           enables debugging/verbose output");
        break;
      case "--debug":
      case "-d":
      case "-v":
        _debug = true;
        debug("Debugging output enabled");
        break;
      case "--configuration":
        i++;
        if (ARGV.length == i) {
          printerr("ERROR: No configuration value was provided");
          return null;
        }

        debug(ARGV[i] + " selected as configuration file");

        if (!GLib.file_test (ARGV[i], GLib.FileTest.EXISTS)) {
            printerr("ERROR: " + ARGV[i] + " does not exists");
            return null;
        }
        if (!GLib.file_test (ARGV[i], GLib.FileTest.IS_REGULAR)) {
            printerr("ERROR: " + ARGV[i] + " is not a regular file");
            return null;
        }

        let kf = new GLib.KeyFile();
        try {
            kf.load_from_file(ARGV[i], GLib.KeyFileFlags.NONE);
        } catch (e) {
            debug(e);
            printerr("ERROR: Could not parse configuration file " + ARGV[i]);
            return null;
        }

        if (!kf.has_group("logger")) {
            printerr("ERROR: "+ARGV[i]+" does not have [logger] section");
            return null;
        }
        try {
            result['admin_server_host'] = kf.get_value("logger", "admin_server_host");
        } catch (e) {
            debug (e);
        }
        try {
            result['admin_server_port'] = kf.get_value("logger", "admin_server_port");
        } catch (e) {
            debug (e);
        }
        break;
    }
  }

  debug ("admin_server_host: " + result['admin_server_host'] + " - admin_server_port: " + result['admin_server_port']);
  return result;
}

//Something ugly to overcome the lack of exit()
options = parse_options ();
if (options != null)
  ml.run();
