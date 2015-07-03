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
const loop           = imports.mainloop;
const JsUnit         = imports.jsUnit;
const FleetCommander = imports.fleet_commander_logger;

let dbus     = null;
let dbusmock = null;

function setUpSuite () {
  let launcher = new Gio.SubprocessLauncher();
  launcher.set_flags(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
  dbus = launcher.spawnv("dbus-daemon --session --print-address --nofork".split(" "));

  let address = Gio.DataInputStream.new (dbus.get_stdout_pipe()).read_line(null, null, null);

  GLib.setenv("DBUS_SESSION_BUS_ADDRESS", address[0].toString(), true);
  launcher.setenv("DBUS_SESSION_BUS_ADDRESS", address[0].toString(), true);
  dbusmock = launcher.spawnv(["./mock_dbus.py"]);

  /* NOTE: We let mock_dbus 500ms time to start.
   * We could wait for the bus name and timeout too
   * and do this more reliable */
  GLib.usleep(500000);
}

function tearDownSuite () {
  if (dbusmock != null) {
    dbusmock.force_exit();
    dbusmock.wait(null);
    dbusmock = null;
  }

  if (dbus != null) {
    dbus.force_exit();
    dbus.wait(null);
    dbus = null;
  }
}

function testInhibitor () {
  let inhibitor = new FleetCommander.ScreenSaverInhibitor();
  JsUnit.assertTrue(inhibitor.cookie == 9191);
  inhibitor.uninhibit();
  JsUnit.assertTrue(inhibitor.cookie == null);
}

let ret = 1;
try {
  setUpSuite();
  ret = JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
} catch (e) {
  tearDownSuite();
  throw e;
}

tearDownSuite();
ret;
