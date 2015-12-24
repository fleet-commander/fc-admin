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

import os
import sys
import json
import unittest
import shutil
import tempfile

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

from fleetcommander import admin as fleet_commander_admin


class MockLibVirtController(object):

    def __init__(self, data_path, username, hostname, mode, admin_hostname, admin_port):

        self.data_dir = os.path.abspath(data_path)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.public_key_file = os.path.join(self.data_dir, 'id_rsa.pub')

        with open(self.public_key_file, 'w') as fd:
            fd.write('PUBLIC_KEY')
            fd.close()

    def list_domains(self):
        return [{'uuid': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'name': 'fedora-unkno'}]

    def session_start(self, uuid):
        return ('someuuid', 0, 'tunnel_pid')

    def session_stop(self, uuid, tunnel_pid):
        pass


class MockWebSocket:

    def __init__(self, **kwargs):
        self.started = False
        self.args = kwargs

    def start(self):
        self.started = True

    def stop(self):
        self.started = False


class TestAdminWSGIRef(unittest.TestCase):

    test_wsgiref = True

    def setUp(self):
        self.test_directory = tempfile.mkdtemp()

        self.args = {
            'host': 'localhost',
            'port': 8777,
            'data_dir': self.test_directory,
            'state_dir': self.test_directory,
            'database_path': os.path.join(self.test_directory, 'database.db'),
        }

        os.environ['FC_TEST_DIRECTORY'] = self.test_directory
        if 'profiles_dir' not in self.args:
            self.args['profiles_dir'] = os.path.join(self.test_directory, 'profiles')
            os.mkdir(self.args['profiles_dir'])

        self.websocket = MockWebSocket()

        # LibVirtController mocker
        fleet_commander_admin.libvirtcontroller.LibVirtController = MockLibVirtController
        self.base_app = fleet_commander_admin.AdminService('__test__', self.args, self.websocket)
        self.base_app.config['TESTING'] = True
        self.app = self.base_app.test_client(stateless=not self.test_wsgiref)

    def tearDown(self):
        shutil.rmtree(self.test_directory)

    def get_data_from_file(self, path):
        return open(path).read()

    def create_dumb_profile (self, payload=None):
        profile = {
                "profile-name": "foo",
                "profile-desc": "bar",
                "users":        "user1,user2,user3",
                "groups":       "group1,group2"
        }

        if not payload:
            payload=profile
        return payload, self.app.post("/profiles/new", data=json.dumps(payload), content_type='application/json')

    def configure_hypervisor(self, host='localhost', username='testuser', mode='session'):
        return self.app.jsonpost('/hypervisor/', data={
            'host': host,
            'username': username,
            'mode': mode,
        })

    def test_00_profiles(self):
        ret = self.app.get("/profiles/")

        INDEX_FILE = os.path.join(self.args['profiles_dir'], 'index.json')

        self.assertEqual(ret.status_code, 200)
        self.assertTrue(os.path.exists(INDEX_FILE),
                        msg='index file was not created')
        indexdata = self.get_data_from_file(INDEX_FILE)
        self.assertEqual(ret.data, indexdata,
                         msg='index content was not correct')

        # Testing of profiles static serving
        ret = self.app.get("/clientdata/index.json")
        self.assertEqual(ret.data, indexdata,
                         msg='Statically served index content was not correct')

    def test_01_profiles_new(self):
        profile, ret = self.create_dumb_profile ()
        self.assertEqual(json.loads(ret.data).get("status", False), "ok")
        self.assertTrue(json.loads(ret.data).get("uid", False))

        uid = json.loads(ret.data)["uid"]
        INDEX_FILE   = os.path.join(self.args['profiles_dir'], 'index.json')
        APPLIES_FILE = os.path.join(self.args['profiles_dir'], 'applies.json')
        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        self.assertEqual(json.loads(self.get_data_from_file (INDEX_FILE))[0]["url"], uid + ".json")
        self.assertEqual(json.loads(self.get_data_from_file (INDEX_FILE))[0]["displayName"], profile["profile-name"])
        self.assertEqual(json.dumps(json.loads(self.get_data_from_file (APPLIES_FILE))[uid]),
                json.dumps({"users": profile["users"].split(","), "groups": profile["groups"].split(",")}))
        self.assertEqual(json.dumps(json.loads(self.get_data_from_file (PROFILE_FILE))),
                json.dumps({"description": profile["profile-desc"], "settings": {}, "name": profile["profile-name"], "uid": uid}))

    def test_02_session_save_empty (self):
        self.configure_hypervisor()

        profile, ret = self.create_dumb_profile ()
        uid = json.loads(ret.data)["uid"]
        self.assertEqual(ret.status_code, 200)

        data = {'domain': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'admin_host': 'localhost', 'admin_port': 8181}
        ret = self.app.jsonpost('/session/start', data=data)
        ret = self.app.jsonpost('/session/save', data={'uid': uid})
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get('/session/stop')
        self.assertEqual(ret.status_code, 200)

    def test_03_session_select_save (self):
        self.configure_hypervisor()

        profile, ret = self.create_dumb_profile ()
        uid = json.loads(ret.data)["uid"]

        data = {'domain': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'admin_host': 'localhost', 'admin_port': 8181}
        ret = self.app.jsonpost('/session/start', data=data)

        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        gsettings = json.loads(self.get_data_from_file (PROFILE_FILE))['settings']
        self.assertEqual(gsettings, {})

        change = {'key': '/foo/bar', 'schema': 'foo', 'value': True, 'signature': 'b'}
        self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change), content_type='application/json')
        ret = self.app.post('/changes/select', data='{"org.gnome.gsettings": ["/foo/bar"]}', content_type='application/json')
        self.assertEqual(ret.status_code, 200)

        ret = self.app.jsonpost('/session/save', data={'uid': uid})
        self.assertEqual(ret.status_code, 200)

        gsettings = json.loads(self.get_data_from_file (PROFILE_FILE))['settings']['org.gnome.gsettings']
        self.assertEqual(len(gsettings), 1)
        self.assertEqual(gsettings[0]["key"], "/foo/bar")
        self.assertEqual(gsettings[0]["value"], True)
        self.assertEqual(gsettings[0]["signature"], "b")

        ret = self.app.get('/session/stop')
        self.assertEqual(ret.status_code, 200)

    def test_04_hypervisor_configuration(self):
        # Hypervisor nor configured yet
        ret = self.app.get('/hypervisor/')
        self.assertEqual(ret.status_code, 200)
        self.assertTrue(ret.jsondata['needcfg'])
        self.assertEqual(ret.jsondata['host'], '')
        self.assertEqual(ret.jsondata['username'], '')
        self.assertEqual(ret.jsondata['mode'], 'system')

        # Save hypervisor configuration
        ret = self.configure_hypervisor()
        self.assertEqual(ret.status_code, 200)

        # Get config again
        ret = self.app.get('/hypervisor/')
        self.assertEqual(ret.status_code, 200)
        self.assertTrue('needcfg' not in ret.jsondata)
        self.assertEqual(ret.jsondata['host'], 'localhost')
        self.assertEqual(ret.jsondata['username'], 'testuser')
        self.assertEqual(ret.jsondata['mode'], 'session')

        # Try to save invalid hypervisor configuration
        ret = self.configure_hypervisor(host='invalid_host_name')
        self.assertEqual(ret.status_code, 200)
        self.assertTrue('errors' in ret.jsondata)
        self.assertTrue('host' in ret.jsondata['errors'])
        self.assertTrue(ret.jsondata['errors']['host'] == 'Invalid hostname specified')

        ret = self.configure_hypervisor(username='0invalid_username')
        self.assertEqual(ret.status_code, 200)
        self.assertTrue('errors' in ret.jsondata)
        self.assertTrue('username' in ret.jsondata['errors'])
        self.assertTrue(ret.jsondata['errors']['username'] == 'Invalid username specified')

        ret = self.configure_hypervisor(mode='invalid_mode')
        self.assertEqual(ret.status_code, 200)
        self.assertTrue('errors' in ret.jsondata)
        self.assertTrue('mode' in ret.jsondata['errors'])
        self.assertTrue(ret.jsondata['errors']['mode'] == 'Invalid session type')

    def test_05_start_invalid_data(self):
        ret = self.app.post('/session/start', data=json.dumps({'whatever': 'something'}), content_type='application/json')
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'Invalid data received'}))
        self.assertEqual(ret.status_code, 400)

    def test_06_session_start_stop(self):
        # Setup hipervisor
        self.configure_hypervisor()

        # Start session
        data = {'domain': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'admin_host': 'localhost', 'admin_port': 8181}
        ret = self.app.jsonpost('/session/start', data=data)
        self.assertEqual(ret.status_code, 200)
        self.assertTrue('websockify_pid' in self.base_app.current_session)
        self.assertTrue(self.base_app.current_session['websockify_pid'] is not None)
        self.assertEqual(self.base_app.current_session['websocket_target_host'], data['admin_host'])
        # TODO: Port is random now
        # self.assertEqual(self.base_app.current_session['websocket_target_port'], 5935)

        ret = self.app.get('/session/stop')
        self.assertEqual(ret.status_code, 200)

        # Attempt to stop without starting a session
        ret = self.app.get('/session/stop')
        self.assertEqual(ret.status_code, 520)

    def test_07_change_select_and_deploy(self):
        # Setup hipervisor
        self.configure_hypervisor()

        # Create dumb profile
        profile_obj = {'profile-name': 'myprofile', 'profile-desc': 'mydesc', 'groups': 'foo,bar', 'users': 'baz'}
        profile_obj, ret = self.create_dumb_profile (payload=profile_obj)
        self.assertEqual(ret.status_code, 200)
        ret_json = json.loads(ret.data)
        self.assertTrue(isinstance(ret_json, dict))
        self.assertTrue('uid' in ret_json)
        uid = ret_json['uid']

        # Start session
        data = {'domain': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'admin_host': 'localhost', 'admin_port': 8181}
        ret = self.app.jsonpost('/session/start', data=data)

        change1 = {'key': '/foo/bar', 'schema': 'foo', 'value': True, 'signature': 'b'}
        ret = self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        change2 = {'key': '/foo/baz', 'schema': 'foo', 'value': True, 'signature': 'b'}
        ret = self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change2), content_type='application/json')
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        # Check all changes
        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(
            json.dumps(json.loads(ret.data)),
            json.dumps({'org.gnome.gsettings': [[change1['key'], change1['value']], [change2['key'], change2['value']]]}))

        # Select changes to save in the profile
        ret = self.app.post('/changes/select', data=json.dumps({'org.gnome.gsettings': [change2['key']]}), content_type='application/json')
        self.assertEqual(ret.status_code, 200)

        payload = json.loads(ret.data)
        self.assertTrue(isinstance(payload, dict))
        self.assertTrue('status' in payload)
        self.assertEqual(payload['status'], 'ok')

        # Save the profile with the selected changes
        ret = self.app.jsonpost("/session/save", data={"uid": uid})
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status": "ok"}))
        self.assertEqual(ret.status_code, 200)

        # Stop the virtual session
        self.app.get('/session/stop')

        # Get index
        ret = self.app.get("/profiles/")
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([{'url': uid + ".json", 'displayName': profile_obj['profile-name']}]))

        # Get profile
        ret = self.app.get("/profiles/"+uid)
        self.assertEqual(ret.status_code, 200)
        profile = json.loads(ret.data)
        self.assertTrue(isinstance(profile, dict))
        self.assertEqual(profile['uid'], uid)
        self.assertEqual(profile['description'], profile_obj['profile-desc'])
        self.assertEqual(profile['name'], profile_obj['profile-name'])
        self.assertEqual(json.dumps(profile['settings']['org.gnome.gsettings'][0]), json.dumps(change2))

        # Get applies
        ret = self.app.get("/profiles/applies")
        self.assertEqual(ret.status_code, 200)
        applies = json.loads(ret.data)
        self.assertTrue(isinstance(applies, dict))
        self.assertTrue(uid in applies)
        self.assertEqual(json.dumps(applies[uid]), json.dumps({'groups': ['foo' , 'bar'], 'users': ['baz']}))
        self.assertEqual(len(applies), 1)

        # Remove profile
        ret = self.app.get("/profiles/delete/"+uid)
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))

        # Check that index is empty
        ret = self.app.get("/profiles/")
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([]))

    def test_08_change_merge_several_changes(self):
        change1 = {'key': '/foo/bar', 'schema': 'foo', 'value': "first", 'signature': 's'}
        ret = self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        change2 = {'key': '/foo/bar', 'schema': 'foo', 'value': 'second', 'signature': 's'}
        ret = self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change2), content_type='application/json')
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'org.gnome.gsettings': [[change2['key'], change2['value']], ]}))

        self.app.get('/session/stop')

    def test_09_empty_collector(self):

        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({}))

    def test_10_libreoffice_and_gsettings_changes(self):

        change_libreoffice = {'key': '/org/libreoffice/registry/foo', 'value': 'bar', 'signature': 's'}
        ret = self.app.post('/changes/submit/org.libreoffice.registry', data=json.dumps(change_libreoffice), content_type='application/json')
        self.assertEqual(json.dumps({'status': 'ok'}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        change_gsettings = {'key': '/foo/bar', 'value': 'bar', 'signature': 's'}
        ret = self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change_gsettings), content_type='application/json')
        self.assertEqual(json.dumps({'status': 'ok'}), json.dumps(json.loads(ret.data)))
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps(
          {'org.gnome.gsettings':      [[change_gsettings['key'],   change_gsettings['value']]],
           'org.libreoffice.registry': [[change_libreoffice['key'], change_libreoffice['value']]]}))

    def test_10_profiles_software(self):
        self.configure_hypervisor()

        profile = {'profile-name': 'myprofile', 'profile-desc': 'mydesc', 'groups': '', 'users': ''}

        profile, ret = self.create_dumb_profile (profile)
        uid = json.loads(ret.data)["uid"]

        # Add GNOME Software overrides
        favourites = json.dumps(['foo.desktop', 'bar.desktop', 'baz.desktop'])
        ret = self.app.post('/profiles/apps/' + uid, content_type='application/json', data=favourites)
        self.assertEqual(json.loads(ret.data).get('status', None), 'ok')
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get("/clientdata/%s.json" % uid)
        profile = json.loads(ret.data)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 1)
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]["key"], "/org/gnome/software/popular-overrides")
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]["value"], favourites)

        # Modify overrides
        favourites = json.dumps(['foo.desktop'])
        ret = self.app.post('/profiles/apps/' + uid, content_type='application/json', data=favourites)
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get("/clientdata/%s.json" % uid)
        profile = json.loads(ret.data)
        self.assertEqual(profile['settings']['org.gnome.gsettings'][0]["value"], favourites)

        # Empty overrides
        favourites = json.dumps([])
        ret = self.app.post('/profiles/apps/' + uid, content_type='application/json', data=favourites)
        self.assertEqual(ret.status_code, 200)

        ret = self.app.get("/clientdata/%s.json" % uid)
        profile = json.loads(ret.data)
        self.assertEqual(len(profile['settings']['org.gnome.gsettings']), 0)

    def test_11_merge_settings(self):
        a = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": False, "signature": "b"}]}
        b = {"org.libreoffice.registry": [{"key": "/org/libreoffice/registry/foo", "value": "asd", "signature": "string"}]}
        c = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": True, "signature": "b"}]}
        d = {"org.gnome.gsettings": [{"key": "/foo/bar", "value": True, "signature": "b"},
                                     {"key": "/foo/bleh", "value": True, "signature": "b"}]}

        ab = fleet_commander_admin.merge_settings(a, b)
        ac = fleet_commander_admin.merge_settings(a, c)
        aa = fleet_commander_admin.merge_settings(a, a)
        ad = fleet_commander_admin.merge_settings(a, d)
        an = fleet_commander_admin.merge_settings(a, {})

        self.assertEqual(len(ab), 2)
        self.assertTrue("org.gnome.gsettings" in ab)
        self.assertTrue("org.libreoffice.registry" in ab)
        self.assertTrue(len(ac["org.gnome.gsettings"]) == 1)
        self.assertTrue(ac["org.gnome.gsettings"][0]["value"] == True)
        self.assertTrue(len(ad["org.gnome.gsettings"]) == 2)
        self.assertTrue(ad["org.gnome.gsettings"][1]["key"] == "/foo/bar")
        self.assertTrue(ad["org.gnome.gsettings"][0]["key"] == "/foo/bleh")

    def test_12_profiles_props(self):
        profile, ret = self.create_dumb_profile()
        uid = json.loads(ret.data)['uid']

        APPLIES_FILE = os.path.join(self.args['profiles_dir'], 'applies.json')
        PROFILE_FILE = os.path.join(self.args['profiles_dir'], uid + '.json')

        # Ammend name
        ret = self.app.jsonpost('/profiles/props/' + uid,
                                data={'profile-name': 'mynewname'})
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.loads(self.get_data_from_file(PROFILE_FILE))['name'], 'mynewname')

        # Ammend description
        ret = self.app.jsonpost('/profiles/props/' + uid,
                                data={'profile-desc': 'somedesc'})
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.loads(self.get_data_from_file(PROFILE_FILE))['description'], 'somedesc')

        ret = self.app.jsonpost('/profiles/props/' + uid,
                                data={'users': 'u1,u2,u3'})
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.loads(self.get_data_from_file(APPLIES_FILE))[uid]['users'],
                         ['u1', 'u2', 'u3'])

        ret = self.app.jsonpost('/profiles/props/' + uid,
                                data={'groups': 'g1,g2,g3'})
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.loads(self.get_data_from_file(APPLIES_FILE))[uid]['groups'],
                         ['g1', 'g2', 'g3'])

class TestAdminApache(TestAdminWSGIRef):
    test_wsgiref = False

if __name__ == '__main__':
    unittest.main()
