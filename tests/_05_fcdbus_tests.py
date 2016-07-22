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

# Set session bus for tests
fcdbus.FleetCommanderDbusClient.DEFAULT_BUS = dbus.SessionBus


class TestDbusService(unittest.TestCase):

    DUMMY_PROFILE = {
        "profile-name": "foo",
        "profile-desc": "bar",
        "users":        "user1,user2,user3",
        "groups":       "group1,group2"
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
            'name': 'Pizza Provider',
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

    def test_00_merge_settings(self):
        a = {'org.gnome.gsettings':
             [{'key': '/foo/bar', 'value': False, 'signature': 'b'}]}
        b = {'org.libreoffice.registry':
             [{'key': '/org/libreoffice/registry/foo',
               'value': 'asd', 'signature': 'string'}]}
        c = {'org.gnome.gsettings':
             [{'key': '/foo/bar', 'value': True, 'signature': 'b'}]}
        d = {'org.gnome.gsettings':
             [{'key': '/foo/bar', 'value': True, 'signature': 'b'},
              {'key': '/foo/bleh', 'value': True, 'signature': 'b'}]}

        ab = fcdbus.merge_settings(a, b)
        ac = fcdbus.merge_settings(a, c)
        aa = fcdbus.merge_settings(a, a)
        ad = fcdbus.merge_settings(a, d)
        an = fcdbus.merge_settings(a, {})

        self.assertEqual(len(ab), 2)
        self.assertTrue("org.gnome.gsettings" in ab)
        self.assertTrue("org.libreoffice.registry" in ab)
        self.assertTrue(len(ac["org.gnome.gsettings"]) == 1)
        self.assertTrue(ac["org.gnome.gsettings"][0]["value"] is True)
        self.assertTrue(len(ad["org.gnome.gsettings"]) == 2)
        self.assertTrue(ad["org.gnome.gsettings"][1]["key"] == "/foo/bar")
        self.assertTrue(ad["org.gnome.gsettings"][0]["key"] == "/foo/bleh")

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

        # Set valid data with not known host
        resp = c.check_hypervisor_config(data)
        self.assertFalse(resp['status'])
        self.assertEqual(resp['fprint'], '2048 SHA256:HASH localhost (RSA)\n')
        self.assertEqual(resp['keys'], 'localhost ssh-rsa KEY\n')

        # Set valid data with known host
        self.ssh.add_keys_to_known_hosts(
            self.known_hosts_file, 'localhost ssh-rsa KEY\n')
        resp = c.check_hypervisor_config(data)
        self.assertTrue(resp['status'])

    def test_03_set_hypervisor_config(self):
        c = fcdbus.FleetCommanderDbusClient()

        data = {
            'host': 'localhost',
            'username': 'valid_user',
            'mode': 'session',
            'adminhost': '',
            'keys': 'myhost ssh-rsa KEY'
        }

        dataresp = data.copy()
        dataresp['pubkey'] = 'PUBLIC_KEY'
        del(dataresp['keys'])

        # Set data
        resp = c.set_hypervisor_config(data)
        self.assertTrue(resp['status'])

        # Retrieve configuration and compare
        self.assertEqual(c.get_hypervisor_config(), dataresp)
        # Check host added to known_hosts
        self.ssh.check_known_host(self.known_hosts_file, data['host'])

    def test_04_new_profile(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a new profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        self.assertTrue(resp['status'])
        uid = self.get_data_from_file(self.INDEX_FILE)[0]['url'].split('.')[0]
        self.assertEqual(resp['uid'], uid)

        # Create malformed index file
        open(self.INDEX_FILE, 'w').write(json.dumps({}))
        resp = c.new_profile(self.DUMMY_PROFILE)
        self.assertFalse(resp['status'])
        self.assertEqual(
            resp['error'],
            '%s does not contain a JSON list as root element' % self.INDEX_FILE)

        # Create malformed applies file
        open(self.INDEX_FILE, 'w').write(json.dumps([]))
        open(self.APPLIES_FILE, 'w').write(json.dumps([]))
        resp = c.new_profile(self.DUMMY_PROFILE)
        self.assertFalse(resp['status'])
        self.assertEqual(
            resp['error'],
            '%s does not contain a JSON object as root element' % self.APPLIES_FILE)

    def test_05_delete_profile(self):
        c = fcdbus.FleetCommanderDbusClient()
        # Delete unexistent profile
        resp = c.delete_profile('fakeuid')
        self.assertTrue(resp['status'])
        # Delete existent profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        resp = c.delete_profile(resp['uid'])
        self.assertTrue(resp['status'])

    def test_06_profile_props(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
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

    def test_07_list_domains(self):
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

    def test_08_session_start(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Start session
        resp = c.session_start('uuid', 'host', '0')
        self.assertTrue(resp['status'])
        self.assertEqual(resp['port'], 8989)

        # Try to start another session
        resp = c.session_start('uuid', 'host', '0')
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'Session already started')

    def test_09_session_stop(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)

        # Stop without previous session start
        resp = c.session_stop()
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'There was no session started')

        # Stop previous started session
        c.session_start('uuid', 'host', '0')
        resp = c.session_stop()
        self.assertTrue(resp['status'])

        # Stop again
        resp = c.session_stop()
        self.assertFalse(resp['status'])
        self.assertEqual(resp['error'], 'There was no session started')

    def test_10_get_submit_select_changes(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start('uuid', 'host', '0')
        # Check for empty changes
        resp = c.get_changes()
        self.assertEqual(resp, {})
        # Add some changes to database
        data = {
            'key': '/foo/bar',
            'schema': 'foo',
            'value': True,
            'signature': 'b'
        }
        c.submit_change('org.gnome.gsettings', data)
        # Check submitted changes
        resp = c.get_changes()
        self.assertEqual(resp, {u'org.gnome.gsettings': [[data['key'], data['value']]]})
        # Select change for profile
        resp = c.select_changes({'org.gnome.gsettings': [data['key']]})
        self.assertTrue(resp['status'])

    def test_11_highlighted_apps(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

#        # Add GNOME Software overrides
        highlightedapps = ['foo.desktop', 'bar.desktop', 'baz.desktop']
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 1)
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]['key'], '/org/gnome/software/popular-overrides')
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]['value'], highlightedapps)

        # Modify overrides
        highlightedapps = ['foo.desktop']
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]["value"], highlightedapps)

        # Empty overrides
        highlightedapps = []
        resp = c.highlighted_apps(highlightedapps, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 0)

    def test_12_empty_session_save(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start('uuid', 'host', '0')

        # Save empty session
        resp = c.session_save(uid)
        self.assertTrue(resp['status'])

    def test_13_session_select_save(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start('uuid', 'host', '0')

        gsettings = self.get_data_from_file(PROFILE_FILE)['settings']
        self.assertEqual(gsettings, {})

        # Submit a change
        change = {'key': '/foo/bar', 'schema': 'foo', 'value': True, 'signature': 'b'}
        resp = c.submit_change('org.gnome.gsettings', change)
        self.assertTrue(resp['status'])

        # Select change
        resp = c.select_changes({'org.gnome.gsettings': ['/foo/bar']})
        self.assertTrue(resp['status'])

        # Save session
        resp = c.session_save(uid)
        self.assertTrue(resp['status'])

        gsettings = self.get_data_from_file(PROFILE_FILE)['settings']['org.gnome.gsettings']
        self.assertEqual(len(gsettings), 1)
        self.assertEqual(gsettings[0]['value'], True)
        self.assertEqual(gsettings[0]['signature'], 'b')

        self.assertEqual(gsettings[0]['key'], '/foo/bar')

    def test_14_get_profiles(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profiles()

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], [{
            'url': '%s.json' % uid,
            'displayName': 'foo'
        }])

    def test_15_get_profile(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profile(uid)

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], {
            'settings': {},
            'uid': uid,
            'name': 'foo',
            'description': 'bar'
        })

    def test_16_get_profile_applies(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        # Get profiles data
        resp = c.get_profile_applies(uid)

        # Check profiles data
        self.assertTrue(resp['status'])
        self.assertEqual(resp['data'], {
            'users': ['user1', 'user2', 'user3'],
            'groups': ['group1', 'group2']
        })

    def test_17_changes_listener(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Configure hypervisor
        self.configure_hypervisor(c)
        # Start a session
        c.session_start('uuid', 'host', '0')
        # Check for empty changes
        resp = c.get_changes()
        self.assertEqual(resp, {})

        # Obtain change listener port
        port = c.get_change_listener_port()

        # Submit changes via changes listener
        data = {
            'key': '/foo/bar',
            'schema': 'foo',
            'value': True,
            'signature': 'b'
        }
        jsondata = json.dumps(data)
        req = urllib2.Request('http://localhost:%s/changes/submit/org.gnome.gsettings' % port, jsondata, {'Content-Type': 'application/json', 'Content-Length': len(jsondata)})
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
        self.assertEqual(response, json.dumps({'status': 'ok'}))

        # Check submitted changes
        resp = c.get_changes()
        self.assertEqual(resp, {u'org.gnome.gsettings': [[data['key'], data['value']]]})

    def test_18_clientdata_serving(self):
        c = fcdbus.FleetCommanderDbusClient()
        port = c.get_change_listener_port()

        # Request empty index
        with self.assertRaisesRegexp(
          urllib2.HTTPError,
          'HTTP Error 404: Not Found'):
            req = urllib2.Request(
                'http://localhost:%s/index.json' % port)
            f = urllib2.urlopen(req)
            response = f.read()
            f.close()

        # Request empty applies
        with self.assertRaisesRegexp(
          urllib2.HTTPError,
          'HTTP Error 404: Not Found'):
            req = urllib2.Request(
                'http://localhost:%s/applies.json' % port)
            f = urllib2.urlopen(req)
            response = f.read()
            f.close()

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
        resp = c.new_profile(self.DUMMY_PROFILE)
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
                    'groups': ['group1', 'group2']
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
                'settings': {}
            }
        )

    def test_19_get_goa_providers(self):
        c = fcdbus.FleetCommanderDbusClient()
        resp = c.get_goa_providers()
        self.assertTrue(resp['status'])
        print resp['providers']
        print self.DUMMY_GOA_PROVIDERS_DATA
        self.assertEqual(resp['providers'], self.DUMMY_GOA_PROVIDERS_DATA)

    def test_20_goa_accounts(self):
        c = fcdbus.FleetCommanderDbusClient()

        # Create a profile
        resp = c.new_profile(self.DUMMY_PROFILE)
        uid = resp['uid']

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        account1 = {
            'Account account_fc_1432373432_0': {
                'Provider': 'provider',
                'MailEnabled': False,
                'DocumentsEnabled': True,
                'ContactsEnabled': False
            }
        }

        account2 = {
            'Account account_fc_1432883432_0': {
                'Provider': 'pizza_provider',
                'PepperoniEnabled': False,
                'CheeseEnabled': True,
                'HotdogEnabled': False
            }
        }

        # Add GOA accounts
        accounts = [account1, account2]
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 2)
        self.assertEqual(goa_accounts[0], account1)
        self.assertEqual(goa_accounts[1], account2)

        # Modify accounts
        accounts = [account2]
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 1)
        self.assertEqual(goa_accounts[0], account2)

        # Empty accounts
        accounts = []
        resp = c.goa_accounts(accounts, uid)
        self.assertTrue(resp['status'])
        profile = self.get_data_from_file(PROFILE_FILE)
        goa_accounts = profile['settings']['org.gnome.online-accounts']
        self.assertEqual(len(goa_accounts), 0)

if __name__ == '__main__':
    unittest.main()
