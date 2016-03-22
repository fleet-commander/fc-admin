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

import os
import signal
import json
import logging
import subprocess
import re

import dbus
import dbus.service
import dbus.mainloop.glib

import gobject

import libvirtcontroller
from database import DBManager

SYSTEM_USER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,30}$')
IPADDRESS_AND_PORT_REGEX = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\:[0-9]{1,5})*$')
HOSTNAME_AND_PORT_REGEX = re.compile(r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])(\:[0-9]{1,5})*$')

DBUS_BUS_NAME = 'org.freedesktop.FleetCommander'
DBUS_OBJECT_PATH = '/org/freedesktop/FleetCommander'
DBUS_INTERFACE_NAME = 'org.freedesktop.FleetCommander'


class FleetCommanderDbusClient(object):
    """
    Fleet commander dbus client
    """

    def __init__(self):
        """
        Class initialization
        """
        self.bus = dbus.SystemBus()
        self.obj = self.bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
        self.iface = dbus.Interface(self.obj, dbus_interface=DBUS_INTERFACE_NAME)

    def get_public_key(self):
        return self.iface.GetPublicKey()

    def get_hypervisor_config(self):
        return json.loads(self.iface.GetHypervisorConfig())

    def set_hypervisor_config(self, data):
        return json.loads(self.iface.SetHypervisorConfig(json.dumps(data)))

    def list_domains(self):
        return json.loads(self.iface.ListDomains())

    def session_start(self, domain_uuid, admin_host, admin_port):
        return json.loads(self.iface.SessionStart(domain_uuid, admin_host, admin_port))

    def session_stop(self, domain_uuid, tunnel_pid):
        return json.loads(self.iface.SessionStop(domain_uuid, tunnel_pid))

    def websocket_start(self, listen_host, listen_port, target_host, target_port):
        return self.iface.WebsocketStart(listen_host, listen_port, target_host, target_port)

    def websocket_stop(self, websockify_pid):
        return self.iface.WebsocketStop(websockify_pid)

    def quit(self):
        return self.iface.Quit()


class FleetCommanderDbusService(dbus.service.Object):

    """
    Fleet commander d-bus service class
    """

    LIST_DOMAINS_RETRIES = 2
    WEBSOCKIFY_COMMAND_TEMPLATE = 'websockify %s:%d %s:%d'
    DNULL = open('/dev/null', 'w')

    def __init__(self, config):
        """
        Class initialization
        """
        super(FleetCommanderDbusService, self).__init__()

        self.config = config

        self.state_dir = config['state_dir']

        # Initialize database
        self.db = DBManager(config['database_path'])

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(DBUS_BUS_NAME, dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self._loop = gobject.MainLoop()
        self._loop.run()

    def get_libvirt_controller(self, admin_host=None, admin_port=None):
        """
        Get a libvirtcontroller instance
        """
        hypervisor = self.db.config['hypervisor']
        return libvirtcontroller.LibVirtController(self.state_dir, hypervisor['username'], hypervisor['host'], hypervisor['mode'], admin_host, admin_port)

    def get_public_key(self):
        # Initialize LibVirtController to create keypair if needed
        ctrlr = libvirtcontroller.LibVirtController(self.state_dir, None, None, 'system', None, None)
        with open(ctrlr.public_key_file, 'r') as fd:
            public_key = fd.read().strip()
            fd.close()
        return public_key

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def GetPublicKey(self):
        return self.get_public_key()

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def GetHypervisorConfig(self):
        public_key = self.get_public_key()
        # Check hypervisor configuration
        data = {
            'pubkey': public_key,
        }
        if 'hypervisor' not in self.db.config:
            data.update({
                'host': '',
                'username': '',
                'mode': 'system',
                'needcfg': True,
                'adminhost': '',
            })
        else:
            data.update(self.db.config['hypervisor'])

        return json.dumps(data)

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='s', out_signature='s')
    def SetHypervisorConfig(self, jsondata):
        data = json.loads(jsondata)
        errors = {}
        # Check username
        if not re.match(SYSTEM_USER_REGEX, data['username']):
            errors['username'] = 'Invalid username specified'
        # Check hostname
        if not re.match(HOSTNAME_AND_PORT_REGEX, data['host']) and not re.match(IPADDRESS_AND_PORT_REGEX, data['host']):
            errors['host'] = 'Invalid hostname specified'
        # Check libvirt mode
        if data['mode'] not in ('system', 'session'):
            errors['mode'] = 'Invalid session type'
        # Check admin host
        if 'adminhost' in data and data['adminhost'] != '':
            if not re.match(HOSTNAME_AND_PORT_REGEX, data['adminhost']) and not re.match(IPADDRESS_AND_PORT_REGEX, data['adminhost']):
                errors['adminhost'] = 'Invalid hostname specified'
        if errors:
            return json.dumps({'status': False, 'errors': errors})
        # Save hypervisor configuration
        self.db.config['hypervisor'] = data
        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def ListDomains(self):
        tries = 0
        while tries < self.LIST_DOMAINS_RETRIES:
            tries += 1
            try:
                domains = self.get_libvirt_controller().list_domains()
                return json.dumps({'status': True, 'domains': domains})
            except Exception as e:
                error = e
        logging.error(error)
        return json.dumps({'status': False, 'error': 'Error retrieving domains'})

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='sss', out_signature='s')
    def SessionStart(self, domain_uuid, admin_host, admin_port):
        try:
            new_uuid, port, tunnel_pid = self.get_libvirt_controller(admin_host, admin_port).session_start(domain_uuid)
        except Exception as e:
            logging.error(e)
            return json.dumps({'status': False, 'error': '%s' % e})
        return json.dumps({
            'status': True,
            'uuid': new_uuid,
            'port': port,
            'tunnel_pid': tunnel_pid,
        })

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='si', out_signature='s')
    def SessionStop(self, domain_uuid, tunnel_pid):
        try:
            self.get_libvirt_controller().session_stop(domain_uuid, tunnel_pid)
        except Exception as e:
            logging.error(e)
            return json.dumps({'status': False, 'error': '%s' % e})
        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='sisi', out_signature='i')
    def WebsocketStart(self, listen_host, listen_port, target_host, target_port):

        command = self.WEBSOCKIFY_COMMAND_TEMPLATE % (
            listen_host, listen_port,
            target_host, target_port,
        )

        process = subprocess.Popen(
            command, shell=True,
            stdin=self.DNULL, stdout=self.DNULL, stderr=self.DNULL)

        return process.pid

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='i', out_signature='')
    def WebsocketStop(self, websockify_pid):
        try:
            os.kill(websockify_pid, signal.SIGKILL)
        except:
            pass

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='')
    def Quit(self):
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
