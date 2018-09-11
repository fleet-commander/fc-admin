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

from __future__ import absolute_import
import os
import sys
import json
import logging
import re
import time
from functools import wraps

import dbus
import dbus.service
import dbus.mainloop.glib

from gi.repository import GObject

from . import sshcontroller
from . import libvirtcontroller
from .database import DBManager
from . import mergers
from .goa import GOAProvidersLoader
from . import fcfreeipa

SYSTEM_USER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,30}$')
IPADDRESS_AND_PORT_REGEX = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\:[0-9]{1,5})*$')
HOSTNAME_AND_PORT_REGEX = re.compile(r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])(\:[0-9]{1,5})*$')

DBUS_BUS_NAME = 'org.freedesktop.FleetCommander'
DBUS_OBJECT_PATH = '/org/freedesktop/FleetCommander'
DBUS_INTERFACE_NAME = 'org.freedesktop.FleetCommander'


def set_last_call_time(f):
    @wraps(f)
    def wrapped(obj, *args, **kwargs):
        obj._last_call_time = time.time()
        r = f(obj, *args, **kwargs)
        return r
    return wrapped


class FleetCommanderDbusClient(object):

    """
    Fleet commander dbus client
    """

    DEFAULT_BUS = dbus.SessionBus
    CONNECTION_TIMEOUT = 1

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
                self.iface = dbus.Interface(
                    self.obj, dbus_interface=DBUS_INTERFACE_NAME)
                return
            except Exception:
                pass
        raise Exception(
            'Timed out trying to connect to fleet commander dbus service')

    def get_initial_values(self):
        return self.iface.GetInitialValues()

    def do_ipa_connection(self):
        return self.iface.DoIPAConnection()

    def heartbeat(self):
        return self.iface.HeartBeat()

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

    def get_global_policy(self):
        return json.loads(self.iface.GetGlobalPolicy())

    def set_global_policy(self, policy):
        return json.loads(self.iface.SetGlobalPolicy(policy))

    def save_profile(self, profiledata):
        return json.loads(self.iface.SaveProfile(json.dumps(profiledata)))

    def get_profiles(self):
        return json.loads(self.iface.GetProfiles())

    def get_profile(self, uid):
        return json.loads(self.iface.GetProfile(uid))

    def delete_profile(self, uid):
        return json.loads(self.iface.DeleteProfile(uid))

    def list_domains(self):
        return json.loads(self.iface.ListDomains())

    def session_start(self, domain_uuid):
        return json.loads(self.iface.SessionStart(domain_uuid))

    def session_stop(self):
        return json.loads(self.iface.SessionStop())

    def session_save(self, uid, data):
        return json.loads(self.iface.SessionSave(uid, json.dumps(data)))

    def is_session_active(self, uuid=''):
        return self.iface.IsSessionActive(uuid)

    def get_change_listener_port(self):
        return self.iface.GetChangeListenerPort()

    def get_goa_providers(self):
        return json.loads(self.iface.GetGOAProviders())

    def quit(self):
        return self.iface.Quit()


class FleetCommanderDbusService(dbus.service.Object):
    """
    Fleet commander d-bus service class
    """

    LIST_DOMAINS_RETRIES = 2

    def __init__(self, args):
        """
        Class initialization
        """
        super(FleetCommanderDbusService, self).__init__()

        # Set log level at initialization
        self.log_level = args['log_level'].lower()
        loglevel = getattr(logging, args['log_level'].upper())
        logging.basicConfig(level=loglevel, format=args['log_format'])

        self.home_dir = os.path.expanduser('~')

        if not os.path.exists(self.home_dir):
            logging.error(
                '%s directory does not exist.\n'
                'In order to have home directory automatically created you '
                'have the following options:\n'
                '- install freeipa-server using `--mkenablehomedir`;\n'
                '- call: `authconfig --enablemkhomedir --update`;\n'
                '- call: `authselect select sssd with-mkhomedir`;\n'
                'The user will have to log into the system in order to have '
                'their home directory created!' % (self.home_dir))
            sys.exit(1)

        if 'state_dir' in args:
            self.state_dir = args['state_dir']
        else:
            # Set state dir to $HOME/.local/share/fleetcommander
            self.state_dir = os.path.join(
                self.home_dir, '.local/share/fleetcommander')

        if not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir)

        self.database_path = os.path.join(self.state_dir, 'fleetcommander.db')

        self.args = args

        self.default_profile_priority = args['default_profile_priority']

        # Load FreeIPA connector
        self.ipa = fcfreeipa.FreeIPAConnector()

        self.GOA_PROVIDERS_FILE = os.path.join(
            args['data_dir'], 'fc-goa-providers.ini')

        # Initialize database
        self.db = DBManager(self.database_path)

        # Initialize change mergers
        self.changemergers = {
            'org.gnome.gsettings':
                mergers.GSettingsChangeMerger(),
            'org.libreoffice.registry':
                mergers.LibreOfficeChangeMerger(),
            'org.chromium.Policies':
                mergers.ChromiumChangeMerger(),
            'com.google.chrome.Policies':
                mergers.ChromiumChangeMerger(),
            'org.mozilla.firefox':
                mergers.FirefoxChangeMerger(),
            'org.freedesktop.NetworkManager':
                mergers.NetworkManagerChangeMerger(),
        }

        # Initialize SSH controller
        self.ssh = sshcontroller.SSHController()
        self.known_hosts_file = os.path.join(self.home_dir, '.ssh/known_hosts')

        # Timeout values
        self.tmp_session_destroy_timeout = float(
            args['tmp_session_destroy_timeout'])
        self.auto_quit_timeout = float(
            args['auto_quit_timeout'])

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(DBUS_BUS_NAME, dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self._loop = GObject.MainLoop()

        # Start session checking
        self.start_session_checking()

        # Set last call time to an initial value
        self._last_call_time = time.time()

        # Enter main loop
        self._loop.run()

    def get_libvirt_controller(self):
        """
        Get a libvirtcontroller instance
        """
        hypervisor = self.db.config['hypervisor']
        return libvirtcontroller.LibVirtController(
            self.state_dir, hypervisor['username'],
            hypervisor['host'], hypervisor['mode'])

    def get_public_key(self):
        # Initialize LibVirtController to create keypair if needed
        ctrlr = libvirtcontroller.LibVirtController(
            self.state_dir, None, None, 'system')
        with open(ctrlr.public_key_file, 'r') as fd:
            public_key = fd.read().strip()
            fd.close()
        return public_key

    def get_hypervisor_config(self):
        logging.debug('Getting hypervisor configuration')
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
                logging.debug(
                    'Getting domain try %s: %s' % (tries, error))
        logging.error('Error retrieving domains %s' % error)
        return None

    def stop_current_session(self):

        if 'uuid' not in self.db.config or \
           'tunnel_pid' not in self.db.config or \
           'port' not in self.db.config:
            logging.error('There was no session started')
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
        self._last_heartbeat = time.time()
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
        logging.debug(
            'Last call time: %s' % self._last_call_time)
        time_passed = time.time() - self._last_heartbeat
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
                        except Exception as e:
                            logging.error(
                                'Error destroying session with UUID %s: %s' %
                                (domain_uuid, e))
            if time.time() - self._last_call_time > self.auto_quit_timeout:
                # Quit service
                logging.debug(
                    'Closing Fleet Commander Admin service due to inactivity')
                self._loop.quit()
            else:
                logging.debug(
                    'Resetting timer for session check')
                self._last_heartbeat = time.time()
        return True

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetInitialValues(self):
        state = {
            'debuglevel': self.log_level,
            'defaults': {
                'profilepriority': self.default_profile_priority,
            }
        }
        return json.dumps(state)

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def DoIPAConnection(self):
        logging.debug('Connecting to IPA server')
        try:
            self.ipa.connect()
            return json.dumps({
                'status': True
            })
        except Exception as e:
            logging.debug(
                'IPA server connection failed: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error connecting to IPA server'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='b')
    def HeartBeat(self):
        # Update last heartbeat time
        self._last_heartbeat = time.time()
        logging.debug(
            'Heartbeat: %s' % self._last_heartbeat)
        return True

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='b')
    def CheckNeedsConfiguration(self):
        return 'hypervisor' not in self.db.config

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetPublicKey(self):
        return self.get_public_key()

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def CheckHypervisorConfig(self, jsondata):
        logging.debug('Checking hypervisor configuration')
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
        if errors:
            return json.dumps({'status': False, 'errors': errors})

        return json.dumps({'status': True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetHypervisorConfig(self):
        return json.dumps(self.get_hypervisor_config())

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SetHypervisorConfig(self, jsondata):
        data = json.loads(jsondata)
        # Save hypervisor configuration
        self.db.config['hypervisor'] = data
        return json.dumps({'status': True})

    @set_last_call_time
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
            except Exception as e:
                logging.error(
                    'Error getting hypervisor fingerprint: %s' % e)
                return json.dumps({
                    'status': False,
                    'error': 'Error connecting to SSH service.'
                })
        else:
            return json.dumps({'status': True})

    @set_last_call_time
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
            except Exception as e:
                logging.error('Error adding host to known hosts: %s' % e)
                return json.dumps({
                    'status': False,
                    'error': 'Error adding host to known hosts'
                })

        return json.dumps({'status': True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='sss', out_signature='s')
    def InstallPubkey(self, hostname, user, passwd):
        host, port = self.parse_hypervisor_hostname(hostname)
        pubkey = self.get_public_key()
        try:
            self.ssh.install_pubkey(
                pubkey, user, passwd, host, port)
            return json.dumps({'status': True})
        except Exception as e:
            logging.error(
                'Error installing public key: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error installing public key'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetGlobalPolicy(self):
        logging.debug('Getting global policy')
        try:
            policy = self.ipa.get_global_policy()
            return json.dumps({'status': True, 'policy': policy})
        except Exception as e:
            logging.error('Error getting global policy: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error getting global policy'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='q', out_signature='s')
    def SetGlobalPolicy(self, policy):

        logging.debug(
            'Setting policy to %s' % policy)

        try:
            self.ipa.set_global_policy(int(policy))
            return json.dumps({'status': True})
        except Exception as e:
            logging.error(
                'Error setting gloal policy to %s: %s' % (policy, e))
            return json.dumps({
                'status': False,
                'error': 'Error setting given global policy'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SaveProfile(self, profiledata):
        logging.debug(
            'Data received for saving profile: %s' % profiledata)

        data = json.loads(profiledata)
        logging.debug(
            'Data after JSON decoding: %s' % data)

        profile = {
            'name': data['name'],
            'description': data['description'],
            'priority': int(data['priority']),
            'settings': data['settings'],
            'groups': [_f for _f in [
                elem.strip() for elem in data['groups'].split(",")] if _f],
            'users': [_f for _f in [
                elem.strip() for elem in data['users'].split(",")] if _f],
            'hosts': [_f for _f in [
                elem.strip() for elem in data['hosts'].split(",")] if _f],
            'hostgroups': [_f for _f in [
                elem.strip() for elem in data['hostgroups'].split(",")] if _f],
        }

        logging.debug(
            'Profile built to be saved: %s' % profile)

        name = profile['name']

        if 'oldname' in data:
            logging.debug(
                'Profile is being renamed from %s to %s' % (
                    data['oldname'], name))
            profile['oldname'] = data['oldname']

        try:
            logging.debug('Saving profile into IPA server')
            self.ipa.save_profile(profile)
            return json.dumps({'status': True})
        except fcfreeipa.RenameToExistingException as e:
            logging.error('Error saving profile %s: %s' % (name, e))
            return json.dumps({
                'status': False,
                'error': '%s' % e
            })
        except Exception as e:
            logging.error('Error saving profile %s: %s' % (name, e))
            return json.dumps({
                'status': False,
                'error': 'Can not save profile.'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetProfiles(self):
        try:
            profiles = self.ipa.get_profiles()
            logging.debug('Profiles data fetched: %s' % profiles)
            return json.dumps({
                'status': True,
                'data': profiles
            })
        except Exception as e:
            logging.error('Error reading profiles from IPA: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error reading profiles index'
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def GetProfile(self, name):
        try:
            profile = self.ipa.get_profile(name)
            logging.debug('Profile data fetched for %s: %s' % (name, profile))
            return json.dumps({
                'status': True,
                'data': profile
            })
        except Exception as e:
            logging.error('Error reading profile %s from IPA: %s' % (name, e))
            return json.dumps({
                'status': False,
                'error': 'Error reading profile %s' % name,
            })

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def DeleteProfile(self, name):
        logging.debug('Deleting profile %s' % name)
        try:
            self.ipa.del_profile(name)
            return json.dumps({'status': True})
        except Exception as e:
            logging.error('Error removing profile %s: %s' % (name, e))
            return json.dumps({'status': False})

    @set_last_call_time
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

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SessionStart(self, domain_uuid):

        logging.debug('Starting new session')

        if self.db.config.get('port', None) is not None:
            logging.error('Session already started')
            return json.dumps({
                'status': False,
                'error': 'Session already started'
            })

        try:
            lvirtctrlr = self.get_libvirt_controller()
            new_uuid, port, tunnel_pid = lvirtctrlr.session_start(domain_uuid)
        except Exception as e:
            logging.error('%s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error starting session'})

        self.db.config['uuid'] = new_uuid
        self.db.config['port'] = port
        self.db.config['tunnel_pid'] = tunnel_pid

        return json.dumps({'status': True, 'port': port})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def SessionStop(self):
        status, msg = self.stop_current_session()
        if status:
            return json.dumps({'status': True})
        else:
            return json.dumps({'status': False, 'error': msg})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def SessionSave(self, uid, data):
        logging.debug('FC: Saving session')
        try:
            profile = self.ipa.get_profile(uid)
        except Exception as e:
            logging.debug('Could not parse profile %s: %s' % (uid, e))
            return json.dumps({
                'status': False,
                'error': 'Could not parse profile %s' % uid
            })

        logging.debug('FC: Loaded profile')

        # Handle changesets
        try:
            changesets = json.loads(data)
        except Exception as e:
            logging.debug(
                'Could not parse changeset: %s. Data: %s' % (e, data))
            return json.dumps({
                'status': False,
                'error': 'Could not parse changesets: %s' % data
            })

        logging.debug('FC: Changesets loaded: %s' % changesets)

        if not isinstance(changesets, dict):
            logging.debug('FC: Invalid changesets data')
            return json.dumps({
                'status': False,
                'error': 'Changesets should be a namespace/changes lists dict'
            })

        # Save changes
        for ns, changeset in changesets.items():
            logging.debug('FC: Processing %s changeset: %s' % (ns, changeset))
            if not isinstance(changeset, list):
                logging.debug('FC: Invalid changeset: %s' % ns)
                return json.dumps({
                    'status': False,
                    'error': 'Changesets should be a change list'
                })

            logging.debug('FC: Adding changes to profile')
            if ns not in profile['settings']:
                logging.debug('FC: Adding new changeset into profile')
                profile['settings'][ns] = changeset
            else:
                if ns in self.changemergers:
                    logging.debug('FC: Merging changeset into profile')
                    profile['settings'][ns] = self.changemergers[ns].merge(
                        profile['settings'][ns],
                        changeset)
                else:
                    logging.debug(
                        'FC: No merger found for %s. Replacing changes' % ns)
                    profile['settings'][ns] = changeset

        logging.debug('FC: Saving profile')
        self.ipa.save_profile(profile)
        logging.debug('FC: Saved profile')

        return json.dumps({'status': True})

    @set_last_call_time
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

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='i')
    def GetChangeListenerPort(self):
        return self.webservice_port

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetGOAProviders(self):
        try:
            loader = GOAProvidersLoader(self.GOA_PROVIDERS_FILE)
            return json.dumps({
                'status': True,
                'providers': loader.get_providers()
            })
        except Exception as e:
            logging.error('Error getting GOA providers data: %s' % e)
            return json.dumps({
                'status': False,
                'error': 'Error getting GOA providers data'
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='')
    def Quit(self):
        self._loop.quit()


if __name__ == '__main__':

    # Python import
    from argparse import ArgumentParser

    # Fleet commander imports
    from .utils import parse_config

    parser = ArgumentParser(description='Fleet Commander Admin dbus service')
    parser.add_argument(
        '--configuration', action='store', metavar='CONFIGFILE', default=None,
        help='Provide a configuration file path for the service')

    args = parser.parse_args()
    config = parse_config(args.configuration)

    svc = FleetCommanderDbusService(config)
    svc.run()
