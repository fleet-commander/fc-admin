#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the licence, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>


# Python imports

# dbus imports

import dbus
import dbus.service
import dbus.mainloop.glib

import gobject

# Fleet commander imports
import libvirtcontroller


class FleetCommanderDbusService(dbus.service.Object):

    """
    Fleet commander d-bus service class
    """

    DBUS_BUS_NAME = 'org.freedesktop.FleetCommander'
    DBUS_OBJECT_PATH = '/org/freedesktop/fleetcommander'

    def __init__(self, config):
        """
        """
        super(FleetCommanderDbusService, self).__init__()
        self.state_dir = config['state_dir']

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(self.DBUS_BUS_NAME, dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, self.DBUS_OBJECT_PATH)
        self._loop = gobject.MainLoop()
        self._loop.run()

    @dbus.service.method('org.freedesktop.fleetcommander', in_signature='', out_signature='s')
    def GetPublicKey(self):
        # Initialize LibVirtController to create keypair if needed
        ctrlr = libvirtcontroller.LibVirtController(self.state_dir, None, None, 'system', None, None)
        with open(ctrlr.public_key_file, 'r') as fd:
            public_key = fd.read().strip()
            fd.close()
        return public_key

    @dbus.service.method('org.freedesktop.fleetcommander', in_signature='', out_signature='s')
    def ListDomains(self):
        pass

    @dbus.service.method('org.freedesktop.fleetcommander', in_signature='', out_signature='s')
    def SessionStart(self):
        pass

    @dbus.service.method('org.freedesktop.fleetcommander', in_signature='', out_signature='s')
    def SessionStop\(self):
        pass

    @dbus.service.method('org.freedesktop.fleetcommander', in_signature='', out_signature='')
    def quit(self):
        self._loop.quit()


if __name__ == '__main__':

    # Python import
    from argparse import ArgumentParser

    # Fleet commander imports
    from utils import parse_config

    parser = ArgumentParser(description='Fleet commander dbus service')
    parser.add_argument(
        '--configuration', action='store', metavar='CONFIGFILE', default=None,
        help='Provide a configuration file path for the service')

    args = parser.parse_args()
    config = parse_config(args.configuration)

    svc = FleetCommanderDbusService(config)
    svc.run()
