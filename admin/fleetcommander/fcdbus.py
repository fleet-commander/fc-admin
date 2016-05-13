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
import uuid
import time

import dbus
import dbus.service
import dbus.mainloop.glib

import gobject

import libvirtcontroller
from database import DBManager
from utils import merge_settings
from collectors import GoaCollector, GSettingsCollector, LibreOfficeCollector

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


    def check_needs_configuration(self):
        return self.iface.CheckNeedsConfiguration()

    def get_public_key(self):
        return self.iface.GetPublicKey()

    def get_hypervisor_config(self):
        return json.loads(self.iface.GetHypervisorConfig())

    def set_hypervisor_config(self, data):
        return json.loads(self.iface.SetHypervisorConfig(json.dumps(data)))

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
        return json.loads(
            self.iface.SessionStart(domain_uuid, admin_host, admin_port))

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

        if 'profiles_dir' not in args:
            args['profiles_dir'] = os.path.join(args['state_dir'], 'profiles')
            if not os.path.exists(args['profiles_dir']):
                os.mkdir(args['profiles_dir'])

        self.args = args
        self.state_dir = args['state_dir']
        self.profiles_dir = args['profiles_dir']

        self.INDEX_FILE = os.path.join(args['profiles_dir'], 'index.json')
        self.APPLIES_FILE = os.path.join(args['profiles_dir'], 'applies.json')

        # Initialize database
        self.db = DBManager(args['database_path'])

        # Initialize collectors
        self.collectors_by_name = {
            'org.gnome.gsettings': GSettingsCollector(self.db),
            # 'org.gnome.online-accounts': GoaCollector(),
            'org.libreoffice.registry': LibreOfficeCollector(self.db),
        }

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
        self.test_and_create_file(self.INDEX_FILE, [])

    def check_for_applies(self):
        self.test_and_create_file(self.APPLIES_FILE, {})

    def test_and_create_file(self, filename, content):
        if os.path.isfile(filename):
            return

        try:
            open(filename, 'w+').write(json.dumps(content))
        except OSError:
            logging.error('There was an error attempting to write on %s' % filename)

    def write_and_close(self, path, load):
        f = open(path, 'w+')
        f.write(load)
        f.close()

    def get_data_from_file(self, path):
        return open(path).read()

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

    def websocket_start(self):
        if 'websockify_pid' in self.db.config and self.db.config['websockify_pid']:
            return

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

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='b')
    def CheckNeedsConfiguration(self):
        return 'hypervisor' not in self.db.config

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetPublicKey(self):
        return self.get_public_key()

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetHypervisorConfig(self):
        return json.dumps(self.get_hypervisor_config())

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
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

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetProfiles(self):
        try:
            self.check_for_profile_index()
            return json.dumps({
                'status': True,
                'data': json.loads(self.get_data_from_file(self.INDEX_FILE))
            })
        except:
            return json.dumps({
                'status': False,
                'error': 'Error reading profiles data from %s' % self.INDEX_FILE
            })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def GetProfile(self, uid):
        try:
            PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid+'.json')
            return json.dumps({
                'status': True,
                'data': json.loads(self.get_data_from_file(PROFILE_FILE))
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
            data = json.loads(self.get_data_from_file(self.APPLIES_FILE))
            return json.dumps({
                'status': True,
                'data': data[uid]
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
        uid = str(uuid.uuid1().int)

        PROFILE_FILE = os.path.join(self.args['profiles_dir'],  uid+'.json')

        profile = {}
        groups = []
        users = []

        groups = [g.strip() for g in data['groups'].split(",")]
        users = [u.strip() for u in data['users'].split(",")]
        groups = filter(None, groups)
        users = filter(None, users)

        profile["uid"] = uid
        profile["name"] = data["profile-name"]
        profile["description"] = data["profile-desc"]
        profile["settings"] = {}

        self.check_for_profile_index()
        index = json.loads(open(self.INDEX_FILE).read())
        if not isinstance(index, list):
            return json.dumps({
                'status': False,
                'error': '%s does not contain a JSON list as root element' % self.INDEX_FILE})
        index.append({"url": uid + ".json", "displayName": data["profile-name"]})

        self.check_for_applies()
        applies = json.loads(open(self.APPLIES_FILE).read())
        if not isinstance(applies, dict):
            return json.dumps({
                'status': False,
                'error': '%s does not contain a JSON object as root element' % self.APPLIES_FILE})
        applies[uid] = {"users": users, "groups": groups}

        self.write_and_close(PROFILE_FILE, json.dumps(profile))
        self.write_and_close(self.APPLIES_FILE, json.dumps(applies))
        self.write_and_close(self.INDEX_FILE, json.dumps(index))

        return json.dumps({'status': True, 'uid': uid})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def DeleteProfile(self, uid):
        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid+'.json')

        try:
            os.remove(PROFILE_FILE)
        except:
            pass

        self.check_for_profile_index()
        index = json.loads(open(self.INDEX_FILE).read())

        for profile in index:
            if (profile["url"] == uid + ".json"):
                index.remove(profile)

        open(self.INDEX_FILE, 'w+').write(json.dumps(index))
        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='ss', out_signature='s')
    def ProfileProps(self, data, uid):
        PROFILE_FILE = os.path.join(self.args['profiles_dir'],  uid+'.json')

        if not os.path.isfile(PROFILE_FILE):
            return json.dumps({'status': False, 'error': 'profile %s does not exist' % uid})

        try:
            payload = json.loads(data)
        except:
            return json.dumps ({
                'status': False,
                'error': 'request data was not a valid JSON object'})

        if not isinstance(payload, dict):
            return json.dumps ({
                'status': False,
                'error': 'request data was not a valid JSON dictionary'})


        if 'profile-name' in payload or 'profile-desc' in payload:
            profile = None
            try:
                profile = json.loads(open(PROFILE_FILE).read())
            except:
                return json.dumps({
                    'status': False,
                    'error': 'could not parse profile %s.json file' % uid})

            if not isinstance(profile, dict):
                return json.dumps({
                    'status': False,
                    'error': 'profile %s.json does not hold a JSON object' % uid})

            if 'profile-name' in payload:
                profile['name'] = payload['profile-name']

            if 'profile-desc' in payload:
                profile['description'] = payload['profile-desc']

            try:
                open(PROFILE_FILE, 'w+').write(json.dumps(profile))
            except:
                return json.dumps({
                    'status': False,
                    'error': 'could not write profile %s.json' % uid})

            # Update profiles index
            if 'profile-name' in payload:
                self.check_for_profile_index()
                index = json.loads(open(self.INDEX_FILE).read())
                if not isinstance(index, list):
                    return json.dumps({
                        'status': False,
                        'error': '%s does not contain a JSON list as root element' % INDEX_FILE})
                for item in index:
                    if item['url'] == '%s.json' % uid:
                        item['displayName'] = payload['profile-name']
                self.write_and_close(self.INDEX_FILE, json.dumps(index))

        if 'users' in payload or 'groups' in payload:
            applies = None
            try:
                applies = json.loads(open(self.APPLIES_FILE).read())
            except:
                return json.dumps({
                    'status': False,
                    'error': 'could not parse applies.json file'})

            if not isinstance(applies, dict):
                return json.dumps({'status': False, 'error': 'applies.json does not hold a JSON object'})

            if 'users' in payload:
                users = [u.strip() for u in payload['users'].split(",")]
                users = filter(None, users)
                applies[uid]['users'] = users

            if 'groups' in payload:
                groups = [g.strip() for g in payload['groups'].split(",")]
                groups = filter(None, groups)
                applies[uid]['groups'] = groups

            try:
                open(self.APPLIES_FILE, 'w+').write(json.dumps(applies))
            except:
                return json.dumps({
                    'status': False,
                    'error': 'could not write applies.json'})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def GetChanges(self):
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

        PROFILE_FILE = os.path.join(
            self.args['profiles_dir'], uid+'.json')

        if not isinstance(data, list) or \
           len(set(map(lambda x: x is unicode, data))) > 1:
            return json.dumps({
                'status': False,
                'error': 'application list is not a list of strings'})

        if not os.path.isfile(self.INDEX_FILE) or not os.path.isfile(PROFILE_FILE):
            return json.dumps({
                'status': False,
                'error': 'there are no profiles in the database'})

        profile = None
        try:
            profile = json.loads(open(PROFILE_FILE).read())
        except:
            return json.dumps({
                'status': False,
                'error': 'could not read profile data'})

        if not isinstance(profile, dict):
            return json.dumps({
                'status': False,
                'error': 'profile object %s is not a dictionary' % uid})

        if not profile.get('settings', False):
            profile['settings'] = {}

        if not isinstance(profile['settings'], dict):
            return json.dumps({
                'status': False,
                'error': 'settings value in %s is not a list' % uid})

        if not profile['settings'].get('org.gnome.gsettings', False):
            profile['settings']['org.gnome.gsettings'] = []

        gsettings = profile['settings']['org.gnome.gsettings']

        if not isinstance(gsettings, list):
            return json.dumps({
                'status': False,
                'error': 'settings/org.gnome.gsettings value in %s is not a list' % uid})

        existing_change = None
        for change in gsettings:
            if 'key' not in change:
                continue

            if change['key'] != '/org/gnome/software/popular-overrides':
                continue

            existing_change = change

        if existing_change and data == []:
            gsettings.remove(existing_change)
        elif not existing_change:
            existing_change = {'key': '/org/gnome/software/popular-overrides',
                               'signature': 'as'}
            gsettings.append(existing_change)

        existing_change['value'] = data

        try:
            open(PROFILE_FILE, 'w+').write(json.dumps(profile))
        except:
            return json.dumps({
                'status': False,
                'error': 'could not write profile %s' % uid})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
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
        return json.dumps({
            'status': False,
            'error': 'Error retrieving domains'
        })

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='sss', out_signature='s')
    def SessionStart(self, domain_uuid, admin_host, admin_port):
        if self.db.config.get('port', None) is not None:
            return json.dumps({
                'status': False,
                'error': 'Session already started'
            })

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
            return json.dumps({
                'status': False,
                'error': 'Error starting session'})

        self.db.config['uuid'] = new_uuid
        self.db.config['port'] = port
        self.db.config['tunnel_pid'] = tunnel_pid

        self.websocket_stop()

        self.db.config['websocket_listen_host'] = unicode(admin_host)
        self.db.config['websocket_listen_port'] = 8989
        self.db.config['websocket_target_host'] = 'localhost'
        self.db.config['websocket_target_port'] = port

        self.websocket_start()

        return json.dumps({'status': True, 'port': 8989})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='', out_signature='s')
    def SessionStop(self):
        if 'uuid' not in self.db.config or 'tunnel_pid' not in self.db.config or 'port' not in self.db.config:
            return json.dumps({
                'status': False,
                'error': 'There was no session started'})

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
            return json.dumps({
                'status': False,
                'error': 'Error stopping session: %s' % e})

        return json.dumps({'status': True})

    @dbus.service.method(DBUS_INTERFACE_NAME,
                         in_signature='s', out_signature='s')
    def SessionSave(self, uid):
        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid+'.json')

        settings = {}

        for name, collector in self.collectors_by_name.items():
            settings[name] = collector.get_settings()

        try:
            profile = json.loads(open(PROFILE_FILE).read())
        except:
            return json.dumps({
                'status': False,
                'error': 'Could not parse profile %s' % uid})

        if not profile.get('settings', False) or \
                not isinstance(profile['settings'], dict) or \
                profile['settings'] == {}:
            profile['settings'] = settings
        else:
            profile['settings'] = merge_settings(profile['settings'], settings)

        self.write_and_close(PROFILE_FILE, json.dumps(profile))

        # TODO: Check if this is really needed
        del(self.db.config['uid'])

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
