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

import sys
import os
import signal
import json
import logging
import subprocess
import re
import uuid
import time

import dbus
import dbus.service
import dbus.mainloop.glib

import gi
gi.require_version('Soup', '2.4')
from gi.repository import GObject, Gio, Soup

import sshcontroller
import libvirtcontroller
from database import DBManager
from utils import get_ip_address, get_data_from_file
import collectors
from goa import GOAProvidersLoader
import profiles

SYSTEM_USER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,30}$')
IPADDRESS_AND_PORT_REGEX = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\:[0-9]{1,5})*$')
HOSTNAME_AND_PORT_REGEX = re.compile(r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])(\:[0-9]{1,5})*$')
CLIENTDATA_REGEX = re.compile(r'^(?P<filename>(index|applies|[0-9]+)\.json)')

DBUS_BUS_NAME = 'org.freedesktop.FleetCommander'
DBUS_OBJECT_PATH = '/org/freedesktop/FleetCommander'
DBUS_INTERFACE_NAME = 'org.freedesktop.FleetCommander'

class FleetCommanderDbusClient(object):

    """
    Fleet commander dbus client
    """

    DEFAULT_BUS = dbus.SystemBus
    CONNECTION_TIMEOUT = 2

    def __init__(self, bus=None):
        """
        Class initialization
        """
        if bus is None:
            bus = self.DEFAULT_BUS()
        self.bus = bus

        t = time.time()
        while time.time() - t < self.CONNECTION_TIMEOUT:
            try:
                self.obj = self.bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
                self.iface = dbus.Interface(self.obj, dbus_interface=DBUS_INTERFACE_NAME)
                return
            except:
                pass
        raise Exception('Timed out trying to connect to fleet commander dbus service')

    def get_initial_values(self):
        return self.iface.GetInitialValues()

    def check_needs_configuration(self):
        return self.iface.CheckNeedsConfiguration()

    def get_public_key(self):
        return self.iface.GetPublicKey()

    def check_hypervisor_config(self, data):
        return json.loads(self.iface.CheckHypervisorConfig(json.dumps(data)))

    def get_hypervisor_config(self):
        return json.loads(self.iface.GetHypervisorConfig())

    def set_hypervisor_config(self, data):
        return json.loads(self.iface.SetHypervisorConfig(json.dumps(data)))

    def check_known_host(self, host):
        return json.loads(self.iface.CheckKnownHost(host))

    def add_known_host(self, host):
        return json.loads(self.iface.AddKnownHost(host))

    def install_pubkey(self, host, user, passwd):
        return json.loads(self.iface.InstallPubkey(
            host, user, passwd
        ))

    def get_profiles(self):
        return json.loads(self.iface.GetProfiles())

    def get_profile(self, uid):
        return json.loads(self.iface.GetProfile(uid))

    def get_profile_applies(self, uid):
        return json.loads(self.iface.GetProfileApplies(uid))

    def new_profile(self, profiledata):
        return json.loads(self.iface.NewProfile(json.dumps(profiledata)))

    def delete_profile(self, uid):
        return json.loads(self.iface.DeleteProfile(uid))

    def profile_props(self, data, uid):
        return json.loads(self.iface.ProfileProps(json.dumps(data), uid))

    def submit_change(self, name, change):
        return json.loads(self.iface.SubmitChange(name, json.dumps(change)))

    def get_changes(self):
        return json.loads(self.iface.GetChanges())

    def select_changes(self, data):
        return json.loads(self.iface.SelectChanges(json.dumps(data)))

    def highlighted_apps(self, data, uid):
        return json.loads(self.iface.HighlightedApps(json.dumps(data), uid))

    def list_domains(self):
        return json.loads(self.iface.ListDomains())

    def session_start(self, domain_uuid, admin_host, admin_port):
        # Admin port is ignored
        return json.loads(
            self.iface.SessionStart(domain_uuid, admin_host))

    def session_stop(self):
        return json.loads(self.iface.SessionStop())

    def session_save(self, uid):
        return json.loads(self.iface.SessionSave(uid))

    def is_session_active(self, uuid=''):
        return self.iface.IsSessionActive(uuid)

    def get_change_listener_port(self):
        return self.iface.GetChangeListenerPort()

    def get_goa_providers(self):
        return json.loads(self.iface.GetGOAProviders())

    def goa_accounts(self, data, uid):
        return json.loads(self.iface.GOAAccounts(json.dumps(data), uid))

    def quit(self):
        return self.iface.Quit()


class FleetCommanderDbusService(dbus.service.Object):

    """
    Fleet commander d-bus service class
    """

    LIST_DOMAINS_RETRIES = 2
    DNULL = open('/dev/null', 'w')

    def __init__(self, args):
        """
        Class initialization
        """
        super(FleetCommanderDbusService, self).__init__()

        if 'profiles_dir' not in args:
            args['profiles_dir'] = os.path.join(args['state_dir'], 'profiles')
            if not os.path.exists(args['profiles_dir']):
                os.mkdir(args['profiles_dir'])

        self.args = args
        self.state_dir = args['state_dir']
        

        self.log_level = args['log_level'].lower()
        loglevel = getattr(logging, args['log_level'].upper())
        logging.basicConfig(level=loglevel, format=args['log_format'])

        self.default_profile_priority = args['default_profile_priority']

        self.profiles = profiles.ProfileManager(
            args['database_path'], args['profiles_dir'])

        # Load previous missing profiles data for retrocompatibility
        self.profiles.load_missing_profiles_data()

        self.profiles_dir = args['profiles_dir']

        self.GOA_PROVIDERS_FILE = os.path.join(
            args['data_dir'], 'fc-goa-providers.ini')

        # Initialize database
        self.db = DBManager(args['database_path'])

        # Initialize collectors
        self.collectors_by_name = {
            'org.gnome.gsettings':
                collectors.GSettingsCollector(self.db),
            'org.libreoffice.registry':
                collectors.LibreOfficeCollector(self.db),
            'org.freedesktop.NetworkManager':
                collectors.NetworkManagerCollector(self.db),
        }

        # Initialize SSH controller
        self.ssh = sshcontroller.SSHController()
        self.known_hosts_file = '/root/.ssh/known_hosts'

        self.webservice_host = args['webservice_host']
        self.webservice_port = int(args['webservice_port'])
        self.client_data_url = args['client_data_url']

        self.tmp_session_destroy_timeout = float(
            args['tmp_session_destroy_timeout'])

    def run(self, sessionbus=False):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        if not sessionbus:
            bus = dbus.SystemBus()
        else:
            bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_BUS_NAME, bus)
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self._loop = GObject.MainLoop()

        # Prepare changes listener
        self.webservice = Soup.Server()
        try:
            address = Gio.InetSocketAddress.new_from_string(
                get_ip_address(self.webservice_host),
                self.webservice_port)
            self.webservice.listen(address, 0)
            if self.webservice_port == 0:
                listeners = self.webservice.get_listeners()
                inetsocket = listeners[0].get_local_address()
                self.webservice_port = inetsocket.get_port()
        except Exception, e:
            logging.error('Error starting webservice: %s' % e)
            sys.exit(1)

        self.webservice.add_handler(
            '/changes/submit/', self.changes_listener_callback)

        self.webservice.add_handler(
            self.client_data_url, self.client_data_callback)

        # Start session checking
        self.start_session_checking()

        # Enter main loop
        self._loop.run()

    def changes_listener_callback(self, server, message, path, query, client,
                                  **kwargs):

        logging.debug('[%s] changes_listener: Request at %s' % (message.method, path))
        # Get changes name
        pathsplit = path[1:].split('/')
        if len(pathsplit) == 3:
            name = pathsplit[2]
            # Get data in message
            try:
                logging.debug('Data received: %s' % message.request_body.data)
                if name in self.collectors_by_name:
                    self.collectors_by_name[name].handle_change(json.loads(message.request_body.data))
                    response = {'status': 'ok'}
                    status_code = Soup.Status.OK
                else:
                    logging.error(
                        'Change submitted for unknown settings name: %s' % name)
                    response = {'status': 'unknown settings name'}
                    status_code = 520
            except Exception, e:
                logging.error(
                    'Error saving changes for setting name %s: %s' % (name, e))
                response = {'status': 'error saving changes'}
                status_code = 520
        else:
            logging.error('Change submited with no settings key name')
            response = {'status': 'error no name'}
            status_code = 520

        message.set_status(status_code)
        message.set_response(
            'application/json',
            Soup.MemoryUse(Soup.MemoryUse.COPY),
            json.dumps(response))

    def client_data_callback(self, server, message, path, query, client,
                             **kwargs):
        logging.debug('[%s] client data: Request at %s' % (message.method, path))
        # Default response and status code
        response = ''
        status_code = 404
        match = re.match(CLIENTDATA_REGEX, path[len(self.client_data_url):])
        if match:
            filename = match.groupdict()['filename']
            filepath = os.path.join(self.args['profiles_dir'], filename)
            logging.debug('Serving %s -> %s' % (filename, filepath))
            try:
                response = get_data_from_file(filepath)
                status_code = 200
            except Exception, e:
                logging.error('clientdata: %s' % e)
        message.set_status(status_code)
        message.set_response(
            'application/json',
            Soup.MemoryUse(Soup.MemoryUse.COPY),
            response)

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

    def get_domains(self, only_temporary=False):
        tries = 0
        while tries < self.LIST_DOMAINS_RETRIES:
            tries += 1
            try:
                domains = self.get_libvirt_controller().list_domains()
                if only_temporary:
                    domains = [d for d in domains if d['temporary']]
                logging.debug('Domains retrieved: %s' % domains)
                return domains
            except Exception as e:
                error = e
                logging.debug('Getting domain try %s: %s' % (tries, error))
        logging.error('Error retrieving domains %s' % error)
        return None

    def stop_current_session(self):
        if 'uuid' not in self.db.config or \
           'tunnel_pid' not in self.db.config or \
           'port' not in self.db.config:
            return False, 'There was no session started'

        domain_uuid = self.db.config['uuid']
        tunnel_pid = self.db.config['tunnel_pid']

        del(self.db.config['uuid'])
        del(self.db.config['tunnel_pid'])
        del(self.db.config['port'])

        try:
            self.get_libvirt_controller().session_stop(domain_uuid, tunnel_pid)
        except Exception as e:
            logging.error('Error stopping session: %s' % e)
            return False, 'Error stopping session: %s' % e

        return True, None

    def start_session_checking(self):
        self._last_changes_request = time.time()
        # Add callback for temporary sessions check
        self.current_session_checking = GObject.timeout_add(
            1000, self.check_running_sessions)
        logging.debug(
            'Started session checking')

    def parse_hypervisor_hostname(self, hostname):
        hostdata = hostname.split()
        if len(hostdata) == 2:
            host, port = hostdata
        else:
            host = hostdata[0]
            port = self.ssh.DEFAULT_SSH_PORT
        return host, port

    def check_running_sessions(self):
        """
        Checks currently running sessions and destroy temporary ones on timeout
        """
        time_passed = time.time() - self._last_changes_request
        logging.debug(
            'Checking running sessions. Time passed: %s' % time_passed)
        if time_passed > self.tmp_session_destroy_timeout:
            domains = self.get_domains(only_temporary=True)
            logging.debug(
                'Currently active temporary sessions: %s' % domains)
            if domains:
                logging.info('Destroying stalled sessions')
                # Stop current session
                current_uuid = self.db.config.get('uuid', False)
                if current_uuid:
                    logging.debug(
                        'Stopping current session: %s' % current_uuid)
                    self.stop_current_session()
                for domain in domains:
                    ctrlr = self.get_libvirt_controller()
                    domain_uuid = domain['uuid']
                    if current_uuid != domain_uuid:
                        try:
                            ctrlr.session_stop(domain_uuid)
                        except Exception, e:
                            logging.error(
                                'Error destroying session with UUID %s: %s' %
                                (domain_uuid, e))
            logging.debug(
                'Resetting timer for session check')
            self._last_changes_request = time.time()
        return True

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetInitialValues(self):
        state = {
            'debuglevel' : self.log_level,
            'defaults' : {
                'profilepriority' : self.default_profile_priority,
            }
        }
        return json.dumps(state)

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='b')
    def CheckNeedsConfiguration(self):
        return 'hypervisor' not in self.db.config

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetPublicKey(self):
        return self.get_public_key()

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def CheckHypervisorConfig(self, jsondata):
        data = json.loads(jsondata)
        errors = {}

        # Check username
        if not re.match(SYSTEM_USER_REGEX, data['username']):
            errors['username'] = 'Invalid username specified'
        # Check hostname
        if not re.match(HOSTNAME_AND_PORT_REGEX, data['host']) \
           and not re.match(IPADDRESS_AND_PORT_REGEX, data['host']):
            errors['host'] = 'Invalid hostname specified'
        # Check libvirt mode
        if data['mode'] not in ('system', 'session'):
            errors['mode'] = 'Invalid session type'
        # Check admin host
        if 'adminhost' in data and data['adminhost'] != '':
            if not re.match(HOSTNAME_AND_PORT_REGEX, data['adminhost']) \
               and not re.match(IPADDRESS_AND_PORT_REGEX, data['adminhost']):
                errors['adminhost'] = 'Invalid hostname specified'
        if errors:
            return json.dumps({'status': False, 'errors': errors})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetHypervisorConfig(self):
        return json.dumps(self.get_hypervisor_config())

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SetHypervisorConfig(self, jsondata):
        data = json.loads(jsondata)
        # Save hypervisor configuration
        self.db.config['hypervisor'] = data
        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def CheckKnownHost(self, hostname):
        host, port = self.parse_hypervisor_hostname(hostname)

        # Check if hypervisor is a known host
        known = self.ssh.check_known_host(
            self.known_hosts_file, host)

        if not known:
            # Obtain SSH fingerprint for host
            try:
                key_data = self.ssh.scan_host_keys(host, port)
                fprint = self.ssh.get_fingerprint_from_key_data(key_data)
                return json.dumps({
                    'status': False,
                    'fprint': fprint,
                    'keys': key_data,
                })
            except Exception, e:
                logging.error(
                    'Error getting hypervisor fingerprint: %s' % e)
                return json.dumps({
                    'status': False,
                    'error': 'Error getting hypervisor fingerprint'
                })
        else:
            return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def AddKnownHost(self, hostname):
        host, port = self.parse_hypervisor_hostname(hostname)

        # Check if hypervisor is a known host
        known = self.ssh.check_known_host(
            self.known_hosts_file, host)

        if not known:
            try:
                self.ssh.add_to_known_hosts(
                    self.known_hosts_file,
                    host, port)
            except Exception, e:
                logging.error('Error adding host to known hosts: %s' % e)
                return json.dumps({
                    'status': False,
                    'error': 'Error adding host to known hosts'
                })

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='sss', out_signature='s')
    def InstallPubkey(self, hostname, user, passwd):
        host, port = self.parse_hypervisor_hostname(hostname)
        pubkey = self.get_public_key()
        try:
            self.ssh.install_pubkey(
                pubkey, user, passwd, host, port)
            return json.dumps({'status': True})
        except Exception, e:
            logging.error(
                'Error installing public key: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error installing public key: %s' % e
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetProfiles(self):
        try:
            return json.dumps({
                'status': True,
                'data': self.profiles.get_index()
            })
        except:
            return json.dumps({
                'status': False,
                'error': 'Error reading profiles index'
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def GetProfile(self, uid):
        try:
            return json.dumps({
                'status': True,
                'data': self.profiles.get_profile(uid)
            })
        except:
            return json.dumps({
                'status': False,
                'error': 'Error reading profile with UID %s' % uid
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def GetProfileApplies(self, uid):
        try:
            return json.dumps({
                'status': True,
                'data': self.profiles.get_applies(uid)
            })
        except:
            return json.dumps({
                'status': False,
                'error': 'Error reading profile with UID %s' % uid
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def NewProfile(self, profiledata):
        data = json.loads(profiledata)

        profile = {
            'name': data['profile-name'],
            'description': data['profile-desc'],
            'priority': data['priority'],
            'settings': {},
            'groups': filter(
                None, [g.strip() for g in data['groups'].split(",")]),
            'users': filter(
                None, [u.strip() for u in data['users'].split(",")]),
        }

        uid = self.profiles.save_profile(profile)

        return json.dumps({'status': True, 'uid': uid})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def DeleteProfile(self, uid):
        self.profiles.remove_profile(uid)
        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def ProfileProps(self, data, uid):
        try:
            profile = self.profiles.get_profile(uid)
        except:
            return json.dumps(
                {'status': False, 'error': 'Can not get profile %s' % uid})

        if not isinstance(profile, dict):
            return json.dumps({
                'status': False,
                'error': 'profile %s.json does not hold a JSON object' % uid})

        try:
            payload = json.loads(data)
        except:
            return json.dumps({
                'status': False,
                'error': 'request data was not a valid JSON object'})

        if not isinstance(payload, dict):
            return json.dumps({
                'status': False,
                'error': 'request data was not a valid JSON dictionary'})

        if 'profile-name' in payload or 'profile-desc' in payload:

            if 'profile-name' in payload:
                profile['name'] = payload['profile-name']

            if 'profile-desc' in payload:
                profile['description'] = payload['profile-desc']

        if 'priority' in payload:
            profile['priority'] = payload['priority']

        if 'users' in payload:
            users = [u.strip() for u in payload['users'].split(",")]
            users = filter(None, users)
            profile['users'] = users

        if 'groups' in payload:
            groups = [g.strip() for g in payload['groups'].split(",")]
            groups = filter(None, groups)
            profile['groups'] = groups

        self.profiles.save_profile(profile)

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetChanges(self):
        # Update last changes request time
        self._last_changes_request = time.time()
        logging.debug(
            'Changes being requested: %s' % self._last_changes_request)

        response = {}

        for namespace, collector in self.collectors_by_name.items():
            if not collector:
                continue

            changes = collector.dump_changes()
            if not changes:
                continue

            response[namespace] = changes

        return json.dumps(response)

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def SubmitChange(self, name, change):
        if name in self.collectors_by_name:
            self.collectors_by_name[name].handle_change(json.loads(change))
            return json.dumps({'status': True})
        else:
            return json.dumps({
                'status': False,
                'error': 'Namespace %s not supported or session not started' % name})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SelectChanges(self, data):
        changes = json.loads(data)

        if self.db.config.get('port', None) is None:
            return json.dumps({
                'status': False, 'error': 'session was not started'})

        for key in changes:
            selection = changes[key]

            if not isinstance(selection, list):
                return json.dumps({
                    'status': False, 'error': 'bad JSON format for %s' % key})

            self.collectors_by_name[key].remember_selected(selection)

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def HighlightedApps(self, payload, uid):

        data = json.loads(payload)

        if not isinstance(data, list) or \
           len(set(map(lambda x: x is unicode, data))) > 1:
            return json.dumps({
                'status': False,
                'error': 'application list is not a list of strings'})

        try:
            profile = self.profiles.get_profile(uid)
        except:
            return json.dumps({
                'status': False,
                'error': 'Can not read profile data for profile %s' % uid})

        if 'org.gnome.gsettings' not in profile['settings']:
            profile['settings']['org.gnome.gsettings'] = []

        gsettings = profile['settings']['org.gnome.gsettings']
        existing_change = None
        for change in gsettings:
            if 'key' not in change:
                continue

            if change['key'] != '/org/gnome/software/popular-overrides':
                continue

            existing_change = change

        if not existing_change:
            existing_change = {'key': '/org/gnome/software/popular-overrides',
                               'signature': 'as'}
            gsettings.append(existing_change)

        if data == []:
            gsettings.remove(existing_change)
        else:
            value = '[%s]' % ','.join(["'%s'" % x for x in data])
            existing_change['value'] = value

        try:
            self.profiles.save_profile(profile)
        except:
            return json.dumps({
                'status': False,
                'error': 'Can not write profile %s' % uid})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def ListDomains(self):
        domains = self.get_domains()
        if domains is not None:
            return json.dumps({'status': True, 'domains': domains})
        else:
            return json.dumps({
                'status': False,
                'error': 'Error retrieving domains'
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def SessionStart(self, domain_uuid, admin_host):

        if self.db.config.get('port', None) is not None:
            return json.dumps({
                'status': False,
                'error': 'Session already started'
            })

        self.db.sessionsettings.clear_settings()

        hypervisor = self.get_hypervisor_config()

        # By default the admin port will be the one we use to listen changes
        admin_port = self.webservice_port
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
            return json.dumps({
                'status': False,
                'error': 'Error starting session'})

        self.db.config['uuid'] = new_uuid
        self.db.config['port'] = port
        self.db.config['tunnel_pid'] = tunnel_pid

        return json.dumps({'status': True, 'port': port})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def SessionStop(self):
        status, msg = self.stop_current_session()
        if status:
            return json.dumps({'status': True})
        else:
            return json.dumps({'status': False, 'error': msg})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SessionSave(self, uid):
        try:
            profile = self.profiles.get_profile(uid)
        except:
            return json.dumps({
                'status': False,
                'error': 'Could not parse profile %s' % uid})

        for name, collector in self.collectors_by_name.items():
            if name not in profile['settings']:
                profile['settings'][name] = collector.get_settings()
            else:
                profile['settings'][name] = collector.merge_settings(
                    profile['settings'][name])

        self.profiles.save_profile(profile)

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='b')
    def IsSessionActive(self, uuid):
        if uuid == '':
            # Asking for current session
            if 'uuid' in self.db.config:
                logging.debug(
                    'Checking for default session with uuid: %s' %
                    self.db.config['uuid'])
                uuid = self.db.config['uuid']
            else:
                logging.debug('Default session not started')
                return False

        domains = self.get_domains()
        for domain in domains:
            if domain['uuid'] == uuid:
                logging.debug(
                    'Session found: %s' % domain)
                return domain['active']
        logging.debug('Given session uuid not found in domains')
        return False

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='i')
    def GetChangeListenerPort(self):
        return self.webservice_port

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetGOAProviders(self):
        try:
            loader = GOAProvidersLoader(self.GOA_PROVIDERS_FILE)
            return json.dumps({
                'status': True,
                'providers': loader.get_providers()
            })
        except Exception, e:
            logging.error('Error getting GOA providers data: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error getting GOA providers data'
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def GOAAccounts(self, payload, uid):

        data = json.loads(payload)

        def check_account(account):
            if isinstance(account, dict):
                keys = account.keys()
                if len(keys) > 2 and 'Template' in keys and 'Provider in keys':
                    for key, value in account.items():
                        if key not in ['Template', 'Provider']:
                            if not key.endswith('Enabled'):
                                return False
                    return True
            return False

        if not isinstance(data, dict):
            return json.dumps({
                'status': False,
                'error': 'accounts data is not a dictionary',
            })

        for account_id, account in data.items():
            invalid = True
            if isinstance(account, dict) and 'Provider' in account.keys():
                for key, value in account.items():
                    if key != 'Provider':
                        if key.endswith('Enabled'):
                            if type(value) != bool:
                                invalid = False
                    else:
                        invalid = False
            if invalid:
                return json.dumps({
                    'status': False,
                    'error': 'malformed goa accounts data received',
                })

        try:
            profile = self.profiles.get_profile(uid)
        except Exception, e:
            return json.dumps({
                'status': False,
                'error': unicode(e),
            })

        if 'settings' not in profile:
            profile['settings'] = {}
        profile['settings']['org.gnome.online-accounts'] = data

        try:
            # profile['uid'] = uid
            self.profiles.save_profile(profile)
        except Exception, e:
            return json.dumps({
                'status': False,
                'error': 'could not write profile %s: %s' % (uid, e)
            })

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='')
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
