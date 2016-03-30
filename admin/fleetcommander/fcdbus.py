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
from utils import merge_settings

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

    DEFAULT_BUS = dbus.SystemBus

    def __init__(self, bus=None):
        """
        Class initialization
        """
        if bus is None:
            bus = dbus.SystemBus()
        self.bus = bus
        self.obj = self.bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
        self.iface = dbus.Interface(self.obj, dbus_interface=DBUS_INTERFACE_NAME)

    def check_needs_configuration(self):
        return self.iface.CheckNeedsConfiguration()

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

    def session_stop(self):
        return json.loads(self.iface.SessionStop())

    def session_save(self, uid):
        return json.loads(self.iface.SessionSave(uid))

    def quit(self):
        return self.iface.Quit()


class FleetCommanderDbusService(dbus.service.Object):

    """
    Fleet commander d-bus service class
    """

    LIST_DOMAINS_RETRIES = 2
    WEBSOCKIFY_COMMAND_TEMPLATE = 'websockify %s:%d %s:%d'
    DNULL = open('/dev/null', 'w')

    def __init__(self, args):
        """
        Class initialization
        """
        super(FleetCommanderDbusService, self).__init__()

        self.args = args

        self.state_dir = args['state_dir']

        # Initialize database
        self.db = DBManager(args['database_path'])

    def run(self, sessionbus=False):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        if not sessionbus:
            bus = dbus.SystemBus()
        else:
            bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_BUS_NAME, bus)
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self._loop = gobject.MainLoop()
        self._loop.run()

    def check_for_profile_index(self):
        INDEX_FILE = os.path.join(self.custom_args['profiles_dir'], 'index.json')
        self.test_and_create_file(INDEX_FILE, [])

    def test_and_create_file(self, filename, content):
        if os.path.isfile(filename):
            return

        try:
            open(filename, 'w+').write(json.dumps(content))
        except OSError:
            logging.error('There was an error attempting to write on %s' % filename)

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

    def get_hypervisor_config(self):
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
        return data

    def websocket_start(self, listen_host, listen_port, target_host, target_port):
        if 'websockify_pid' in self.db.config and self.db.config['websockify_pid']:
            return

        self.db.config.setdefault('websocket_listen_host', listen_host)
        self.db.config.setdefault('websocket_listen_port', listen_port)
        self.db.config.setdefault('websocket_target_host', target_host)
        self.db.config.setdefault('websocket_target_port', target_port)

        command = self.WEBSOCKIFY_COMMAND_TEMPLATE % (
            self.db.config['websocket_listen_host'],
            self.db.config['websocket_listen_port'],
            self.db.config['websocket_target_host'],
            self.db.config['websocket_target_port'],
        )

        process = subprocess.Popen(
            command, shell=True,
            stdin=self.DNULL, stdout=self.DNULL, stderr=self.DNULL)

        self.db.config['websockify_pid'] = process.pid

    def websocket_stop(self):
        if 'websockify_pid' in self.db.config and self.db.config['websockify_pid']:
            try:
                os.kill(self.db.config['websockify_pid'], signal.SIGKILL)
            except:
                pass
            del(self.db.config['websockify_pid'])

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='b')
    def CheckNeedsConfiguration(self):
        return 'hypervisor' not in self.db.config

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def GetPublicKey(self):
        return self.get_public_key()

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def GetHypervisorConfig(self):
        return json.dumps(self.get_hypervisor_config)

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

        if self.db.config.get('port', None) is not None:
            return json.dumps({'status': 'Session already started'})

        self.db.sessionsettings.clear_settings()

        hypervisor = self.get_hypervisor_config()

        forcedadminhost = hypervisor.get('adminhost', None)
        if forcedadminhost:
            forcedadminhostdata = forcedadminhost.split(':')
            if len(forcedadminhostdata) < 2:
                forcedadminhostdata.append(admin_port)
            admin_host, admin_port = forcedadminhostdata

        try:
            new_uuid, port, tunnel_pid = self.get_libvirt_controller(admin_host, admin_port).session_start(domain_uuid)
        except Exception as e:
            logging.error(e)
            return json.dumps({'status': False, 'error': 'Error starting session'})

        self.db.config['uuid'] = new_uuid
        self.db.config['port'] = port
        self.db.config['tunnel_pid'] = tunnel_pid

        self.websocket_stop()

        self.db.config['websocket_listen_host'] = admin_host
        self.db.config['websocket_target_host'] = 'localhost'
        self.db.config['websocket_target_port'] = port
        self.websocket_start()

        return json.dumps({'port': 8989})

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def SessionStop(self):
        if 'uuid' not in self.db.config or 'tunnel_pid' not in self.db.config or 'port' not in self.db.config:
            return json.dumps({'status': False, 'error': 'There was no session started'})

        domain_uuid = self.db.config['uuid']
        tunnel_pid = self.db.config['tunnel_pid']

        del(self.db.config['uuid'])
        del(self.db.config['tunnel_pid'])
        del(self.db.config['port'])

        self.websocket_stop()

        try:
            self.get_libvirt_controller().session_stop(domain_uuid, tunnel_pid)
        except Exception as e:
            logging.error(e)
            return json.dumps({'status': False, 'error': 'Error stopping session: %s' % e})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='s', out_signature='s')
    def SessionSave(self, uid):
        PROFILE_FILE = os.path.join(self.custom_args['profiles_dir'], uid+'.json')

        settings = {}

        for name, collector in self.collectors_by_name.items():
            settings[name] = collector.get_settings()

        try:
            profile = json.loads(open(PROFILE_FILE).read())
        except:
            return json.dumps({'status': False, 'error': 'Could not parse profile %s' % uid})

        if not profile.get('settings', False) or \
                not isinstance(profile['settings'], dict) or \
                profile['settings'] == {}:
            profile['settings'] = settings
        else:
            profile['settings'] = merge_settings(profile['settings'], settings)

        self.write_and_close(PROFILE_FILE, json.dumps(profile))

        del(self.current_session["uid"])

        return json.dumps({'status': True})

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
