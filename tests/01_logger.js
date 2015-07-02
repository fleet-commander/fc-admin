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
const loop           = imports.mainloop;

let dbus;
let dbusmock;

function setUpSuite () {
  let launcher = new Gio.SubprocessLauncher();
  launcher.set_flags(Gio.SubprocessFlags.STDOUT_PIPE);
  dbus = launcher.spawnv("dbus-daemon --session --print-address --nofork".split(" "));

  let address = Gio.DataInputStream.new (dbus.get_stdout_pipe()).read_line(null, null, null);
  GLib.setenv("DBUS_SESSION_BUS_ADDRESS", address[0].toString(), true);
  launcher.setenv("DBUS_SESSION_BUS_ADDRESS", address[0].toString(), true);
  dbusmock = launcher.spawnv("python -m dbusmock org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver".split(" "));

  let bus = Gio.bus_get_sync(Gio.BusType.SESSION, null);
  let proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, null,
                                      'org.freedesktop.ScreenSaver', '/ScreenSaver',
                                      'org.freedesktop.ScreenSaver', null);
}

function tearDownSuite () {
  dbusmock.force_exit();
  dbusmock.wait(null);
  dbus.force_exit();
  dbus.wait(null);
}

function testInhibitor () {
  let inhibitor = new FleetCommander.ScreenSaverInhibitor();
  JsUnit.assertFalse(inhibitor.cookie == null);
  inhibitor.uninhibit();
  JsUnit.assertTrue(inhibitor.cookie == null);
}


setUpSuite();
let ret = JsUnit.gjstestRun(this, JsUnit.setUp, JsUnit.tearDown);
tearDownSuite();

ret;
