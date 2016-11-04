#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2015 Red Hat, Inc.
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
import os
import sys
import shutil
import tempfile
import subprocess
import time
import unittest
import json
import urllib2

import dbus

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

# Fleet commander imports
from fleetcommander import fcdbus
from fleetcommander import sshcontroller

# Tests imports
from test_fcdbus_service import MockLibVirtController


class TestDbusClient(fcdbus.FleetCommanderDbusClient):
    DEFAULT_BUS = dbus.SessionBus

# Mock dbus client
fcdbus.FleetCommanderDbusClient = TestDbusClient


class TestDbusService(unittest.TestCase):

    maxDiff = None

    TEMPLATE_UUID = 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81'
    SESSION_UUID = 'fefb45d9-5a81-3392-b7bc-e2e37c2d'

    DUMMY_PROFILE_PAYLOAD = {
        "profile-name": "foo",
        "profile-desc": "bar",
        "users":        "user1,user2,user3",
        "groups":       "group1,group2",
        "priority":      51, 
        "hosts":      "testhost1,testhost2",
    }

    MAX_DBUS_CHECKS = 10

    DUMMY_GOA_PROVIDERS_DATA = {
        'provider': {
            'name': 'Provider',
            'services': {
                'MailEnabled': {'enabled': True, 'name': 'Mail'},
                'DocumentsEnabled': {'enabled': True, 'name': 'Documents'}
            }
        },
        'pizza_provider': {
            'name': 'My Pizza Provider',
            'services': {
                'HotdogEnabled': {'enabled': False, 'name': 'Hotdog'},
                'PizzaEnabled': {'enabled': True, 'name': 'Pizza'},
                'PepperoniEnabled': {'enabled': True, 'name': 'Pepperoni'}
            }
        },
        'special_provider': {
            'name': 'Special Provider',
            'services': {
                'Enabled': {'enabled': True, 'name': 'Enabled'},
            }
        },
    }

    def setUp(self):
        self.test_directory = tempfile.mkdtemp()

        self.args = {
            'webservice_host': 'localhost',
            'webservice_port': '0',
            'state_dir': self.test_directory,
            'profiles_dir': os.path.join(self.test_directory, 'profiles'),
            'database_path': os.path.join(self.test_directory, 'database.db'),
            'tmp_session_destroy_timeout': 60,
        }

        self.INDEX_FILE = os.path.join(self.args['profiles_dir'], 'index.json')
        self.APPLIES_FILE = os.path.join(self.args['profiles_dir'], 'applies.json')

        # Open service
        self.service = subprocess.Popen([
            os.path.join(
                os.environ['TOPSRCDIR'],
                'tests/test_fcdbus_service.py'),
            self.test_directory,
        ])

        checks = 0
        while True:
            try:
                c = fcdbus.FleetCommanderDbusClient()
                c.get_public_key()
                break
            except:
                checks += 1
                if checks < self.MAX_DBUS_CHECKS:
                    time.sleep(0.1)
                else:
                    raise Exception(
                        'Test error: ' +
                        'DBUS Service is getting too much to start')

        self.ssh = sshcontroller.SSHController()
        self.known_hosts_file = os.path.join(
            self.args['state_dir'], 'known_hosts')

    def tearDown(self):
        # Kill service
        self.service.kill()
        shutil.rmtree(self.test_directory)

    def get_data_from_file(self, path):
        """
        Reads JSON file contents
        """
        return json.loads(open(path).read())

    def configure_hypervisor(self, c):
        # Configure hypervisor
        c.set_hypervisor_config({
            'host': 'myhost',
            'username': 'valid_user',
            'mode': 'session',
            'adminhost': '',
            'keys': 'myhost ssh-rsa KEY'
        })

    def test_00_get_initial_values(self):
        c = fcdbus.FleetCommanderDbusClient()

        state = {
            'debuglevel' : "debug",
            'defaults' : {
                'profilepriority' : 50,
            }
        }

        self.assertEqual(json.loads(c.get_initial_values()), state)

    def test_01_get_public_key(self):
        c = fcdbus.FleetCommanderDbusClient()
        self.assertEqual(c.get_public_key(), 'PUBLIC_KEY')

    def test_02_get_hypervisor_config(self):
        c = fcdbus.FleetCommanderDbusClient()
        self.assertEqual(c.get_hypervisor_config(), {
            'pubkey': 'PUBLIC_KEY',
            'host': '',
            'username': '',
            'mode': 'system',
            'needcfg': True,
            'adminhost': '',
        })

    def test_03_check_hypervisor_config(self):
        c = fcdbus.FleetCommanderDbusClient()

        data = {
            'host': 'localhost',
            'username': 'valid_user',
            'mode': 'session',
            'adminhost': '',
        }

        # Set invalid host data
        idata = data.copy()
        idata['host'] = 'invalid_host'
        resp = c.check_hypervisor_config(idata)
        self.assertFalse(resp['status'])
        self.assertEqual(
            resp['errors'], {'host': 'Invalid hostname specified'})

        # Set invalid username data
        idata = data.copy()
        idata['username'] = 'invalid#username'
        resp = c.check_hypervisor_config(idata)
        self.assertFalse(resp['status'])
        self.assertEqual(
            resp['errors'], {'username': 'Invalid username specified'})

        # Set invalid session data
        idata = data.copy()
        idata['mode'] = 'invalidmode'
        resp = c.check_hypervisor_config(idata)
        self.assertFalse(resp['status'])
        self.assertEqual(resp['errors'], {'mode': 'Invalid session type'})

    def test_04_set_hypervisor_config(self):
        c = fcdbus.FleetCommanderDbusClient()

        data = {
            'host': 'localhost',
            'username': 'valid_user',
            'mode': 'session',
            'adminhost': ''
        }

        dataresp = data.copy()
        dataresp['pubkey'] = 'PUBLIC_KEY'

        # Set data
        resp = c.set_hypervisor_config(data)
        self.assertTrue(resp['status'])

        # Retrieve configuration and compare
        self.assertEqual(c.get_hypervisor_config(), dataresp)

    def test_05_check_known_host(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Check not known host
        resp = c.check_known_host('localhost')
        self.assertFalse(resp['status'])
        self.assertEqual(resp['fprint'], '2048 SHA256:HASH localhost (RSA)\n')
        self.assertEqual(resp['keys'], 'localhost ssh-rsa KEY\n')

        # Add host to known hosts
        self.ssh.add_keys_to_known_hosts(
            self.known_hosts_file, 'localhost ssh-rsa KEY\n')

        # Check already known host
        resp = c.check_known_host('localhost')
        self.assertTrue(resp['status'])

    def test_06_add_known_host(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Check not known host
        resp = c.check_known_host('localhost')
        self.assertFalse(resp['status'])

        # Add host to known hosts
        c.add_known_host('localhost')

        # Check already known host
        resp = c.check_known_host('localhost')
        self.assertTrue(resp['status'])

    def test_07_install_public_key(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Test install with bad credentials
        resp = c.install_pubkey(
            'localhost',
            'username',
            'badpassword',
        )
        self.assertFalse(resp['status'])

        # Test install with correct credentials
        resp = c.install_pubkey(
            'localhost',
            'username',
            'password',
        )
        self.assertTrue(resp['status'])

    def test_08_new_profile(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a new profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        self.assertTrue(resp['status'])
        uid = self.get_data_from_file(self.INDEX_FILE)[0]['url'].split('.')[0]
        self.assertEqual(resp['uid'], uid)

    def test_09_delete_profile(self):
        c = fcdbus.FleetCommanderDbusClient()
        # Delete unexistent profile
        resp = c.delete_profile('fakeuid')
        self.assertTrue(resp['status'])
        # Delete existent profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        resp = c.delete_profile(resp['uid'])
        self.assertTrue(resp['status'])

    def test_10_profile_props(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Ammend name
        resp = c.profile_props({'profile-name': 'mynewname'}, uid)
        self.assertTrue(resp['status'])
        self.assertEqual(self.get_data_from_file(PROFILE_FILE)['name'], 'mynewname')

        # Check index file is being updated accordingly
        entry = {'url': '%s.json' % uid, 'displayName': 'wrongDisplayName'}
        for e in self.get_data_from_file(self.INDEX_FILE):
            if e['url'] == '%s.json' % uid:
                entry = e
                break;
        self.assertEqual(entry['displayName'], 'mynewname')

        # Ammend description
        resp = c.profile_props({'profile-desc': 'somedesc'}, uid)
        self.assertTrue(resp['status'])
        self.assertEqual(self.get_data_from_file(PROFILE_FILE)['description'], 'somedesc')

        # Ammend users
        resp = c.profile_props({'users': 'u1,u2,u3'}, uid)
        self.assertTrue(resp['status'])
        self.assertEqual(self.get_data_from_file(self.APPLIES_FILE)[uid]['users'], ['u1', 'u2', 'u3'])

        # Ammend groups
        resp = c.profile_props({'groups': 'g1,g2,g3'}, uid)
        self.assertTrue(resp['status'])
        self.assertEqual(self.get_data_from_file(self.APPLIES_FILE)[uid]['groups'], ['g1', 'g2', 'g3'])

    def test_11_list_domains(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Try to get domains without configuring hypervisor
        resp = c.list_domains()
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'Error retrieving domains')

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Get domains
        resp = c.list_domains()
        self.assertTrue(resp['status'])
        self.assertEqual(resp['domains'], MockLibVirtController.DOMAINS_LIST)

    def test_12_session_start(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Start session
        resp = c.session_start(self.TEMPLATE_UUID, 'host', '5')
        self.assertTrue(resp['status'])
        self.assertEqual(resp['port'], 0)

        # Try to start another session
        resp = c.session_start(self.TEMPLATE_UUID, 'host', '0')
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'Session already started')

    def test_13_session_stop(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Stop without previous session start
        resp = c.session_stop()
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'There was no session started')

        # Stop previous started session
        c.session_start(self.TEMPLATE_UUID, 'host', '0')
        resp = c.session_stop()
        self.assertTrue(resp['status'])

        # Stop again
        resp = c.session_stop()
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'There was no session started')

    def test_15_highlighted_apps(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

#        # Add GNOME Software overrides
        highlightedapps = ['foo.desktop', 'bar.desktop', 'baz.desktop']
        highlightedappsstring = "['foo.desktop','bar.desktop','baz.desktop']"
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 1)
        self.assertEqual(
            profile['settings']['org.gnome.gsettings'][0]['key'],
            '/org/gnome/software/popular-overrides')
        self.assertEqual(
            profile['settings']['org.gnome.gsettings'][0]['value'],
            highlightedappsstring)

        # Modify overrides
        highlightedapps = ['foo.desktop']
        highlightedappsstring = "['foo.desktop']"
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(
            profile['settings']['org.gnome.gsettings'][0]["value"],
            highlightedappsstring)

        # Empty overrides
        highlightedapps = []
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 0)

    def test_16_empty_session_save(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start(self.TEMPLATE_UUID, 'host', '0')

        # Save empty session
        resp = c.session_save(uid, {})
        self.assertTrue(resp['status'])

    def test_17_session_save(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start(self.TEMPLATE_UUID, 'host', '0')

        gsettings = self.get_data_from_file(PROFILE_FILE)['settings']
        self.assertEqual(gsettings, {})

        # Save session
        # TODO: Settings for session saving
        settings = {
            'org.gnome.gsettings': [{
                'value': True,
                'key': '/foo/bar',
                'signature': 'b'
            }]
        }
        resp = c.session_save(uid, settings)
        self.assertTrue(resp['status'])

        gsettings = self.get_data_from_file(
            PROFILE_FILE)['settings']['org.gnome.gsettings']
        self.assertEqual(len(gsettings), 1)
        self.assertEqual(gsettings[0]['value'], True)
        self.assertEqual(gsettings[0]['signature'], 'b')
        self.assertEqual(gsettings[0]['key'], '/foo/bar')

    def test_18_get_profiles(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profiles()

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], [{
            'url': '%s.json' % uid,
            'displayName': 'foo'
        }])

    def test_19_get_profile(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profile(uid)

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], {
            'settings': {},
            'uid': uid,
            'name': 'foo',
            'description': 'bar',
            'users': ['user1', 'user2', 'user3'],
            'groups': ['group1', 'group2'],
            'priority': 51,
            'hosts': ['testhost1','testhost2'],

        })

    def test_20_get_profile_applies(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profile_applies(uid)

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], {
            'users': ['user1', 'user2', 'user3'],
            'groups': ['group1', 'group2'],
            'hosts': ['testhost1','testhost2'],
        })

    def test_22_clientdata_serving(self):
        c = fcdbus.FleetCommanderDbusClient()
        port = c.get_change_listener_port()

        # Request non existent profile
        with self.assertRaisesRegexp(
          urllib2.HTTPError,
          'HTTP Error 404: Not Found'):
            inexistentuid = '94484425290563468736752948271916980692'
            req = urllib2.Request(
                'http://localhost:%s/%s.json' % (
                    port, inexistentuid))
            f = urllib2.urlopen(req)
            response = f.read()
            f.close()

        # Create profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        # Request index
        req = urllib2.Request(
            'http://localhost:%s/index.json' % port)
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
        self.assertEqual(
            json.loads(response),
            [
                {
                    'url': '%s.json' % uid,
                    'displayName': 'foo'
                }
            ]
        )

        # Request applies
        req = urllib2.Request(
            'http://localhost:%s/applies.json' % port)
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
        self.assertEqual(
            json.loads(response),
            {
                uid: {
                    'users': ['user1', 'user2', 'user3'],
                    'groups': ['group1', 'group2'],
                    'hosts': ['testhost1','testhost2'],
                }
            }
        )

        # Request profile
        req = urllib2.Request(
            'http://localhost:%s/%s.json' % (port, uid))
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
        self.assertEqual(
            json.loads(response),
            {
                'name': 'foo',
                'uid': uid,
                'description': 'bar',
                'settings': {},
                'priority': 51,
            }
        )

    def test_23_get_goa_providers(self):
        c = fcdbus.FleetCommanderDbusClient()
        resp = c.get_goa_providers()
        self.assertTrue(resp['status'])
        self.assertEqual(resp['providers'], self.DUMMY_GOA_PROVIDERS_DATA)

    def test_24_goa_accounts(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE_PAYLOAD)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        account1_id = 'Account account_fc_1432373432_0'
        account1 = {
            'Provider': 'provider',
            'MailEnabled': False,
            'DocumentsEnabled': True,
            'ContactsEnabled': False
        }

        account2_id = 'Account account_fc_1432883432_0'
        account2 = {
            'Provider': 'pizza_provider',
            'PepperoniEnabled': False,
            'CheeseEnabled': True,
            'HotdogEnabled': False
        }

        accounts = {
            account1_id: account1,
            account2_id: account2
        }

        # Add GOA accounts
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 2)
        self.assertEqual(goa_accounts[account1_id], account1)
        self.assertEqual(goa_accounts[account2_id], account2)

        # Modify accounts
        del accounts[account1_id]
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 1)
        self.assertEqual(goa_accounts[account2_id], account2)

        # Empty accounts
        accounts = {}
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 0)

    def test_24_is_session_active(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Check current session active without starting any
        resp = c.is_session_active()
        self.assertFalse(resp)

        # Check current session active after started current session
        print c.session_start(self.TEMPLATE_UUID, 'host', '5')
        resp = c.is_session_active()
        self.assertTrue(resp)

        # Check non existent session by its uuid
        resp = c.is_session_active('unkknown')
        self.assertFalse(resp)

        # Check existent session by its uuid
        resp = c.is_session_active('')
        self.assertTrue(resp)

if __name__ == '__main__':
    unittest.main()
