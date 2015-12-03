#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

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
import requests

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

from fleetcommander import admin as fleet_commander_admin

class MockResponse:
    pass

class MockRequests:
    DEFAULT_CONTENT = "SOMECONTENT"
    DEFAULT_STATUS = 200
    exceptions = requests.exceptions

    def __init__(self):
        self.queue = []
        self.raise_error = False
        self.set_default_values()

    def get(self, url):
        print("--> "+url)
        if self.raise_error:
            raise requests.exceptions.ConnectionError('Connection failed!')
        self.queue.append(url)
        ret = MockRequests()
        ret.content = self.content
        ret.status_code = self.status_code
        return ret

    def pop(self):
        return self.queue.pop()

    def set_default_values(self):
        self.content = self.DEFAULT_CONTENT
        self.status_code = self.DEFAULT_STATUS
        self.raise_error = False

    def raise_error_on_get(self):
        self.raise_error = True


class MockVncWebSocket:

    def __init__(self, **kwargs):
        self.started = False
        self.args = kwargs

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

# assigned mocked objects


class TestAdminWSGIRef(unittest.TestCase):

    test_wsgiref = True

    cookie = "/tmp/fleet-commander-start"
    args = {
        'host': 'localhost',
        'port': 8777,
        'data_dir': PYTHONPATH,
        'database_path': tempfile.mktemp(),
    }

    def setUp(self):
        fleet_commander_admin.requests.set_default_values()
        if 'profiles_dir' not in self.args:
            self.args['profiles_dir'] = tempfile.mkdtemp()

        self.vnc_websocket = MockVncWebSocket()
        self.base_app = fleet_commander_admin.AdminService('__test__', self.args, self.vnc_websocket)
        self.base_app.config['TESTING'] = True
        self.app = self.base_app.test_client(stateless=not self.test_wsgiref)

    @classmethod
    def setUpClass(cls):
        fleet_commander_admin.requests = MockRequests()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.args['profiles_dir'])
        cls.args['profiles_dir'] = tempfile.mkdtemp()

    def get_data_from_file(self, path):
        return open(path).read()

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

    def test_01_attempt_save_unselected_profile(self):
        profile_id = '0123456789'
        profile_data = json.dumps(dict(name='myprofile', description='mydesc', settings={}, groups='', users=''))
        ret = self.app.post('/profiles/save/' + profile_id, data=profile_data, content_type='application/json')

        PROFILE = os.path.join(self.args['profiles_dir'], profile_id + '.json')
        self.assertFalse(os.path.exists(PROFILE), msg='profile file was not created')
        self.assertEqual(ret.status_code, 403)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status": "nonexistinguid"}))

    def test_02_session_start_stop(self):
        # Start session
        host = 'somehost'
        ret = self.app.post('/session/start', data=json.dumps({'host': host}), content_type='application/json')

        self.assertTrue('websockify_pid' in self.base_app.current_session)
        self.assertTrue(self.base_app.current_session['websockify_pid'] is not None)
        self.assertEqual(self.base_app.current_session['websocket_target_host'], host)
        self.assertEqual(self.base_app.current_session['websocket_target_port'], 5935)

        self.assertEqual(ret.data, MockRequests.DEFAULT_CONTENT)
        self.assertEqual(ret.status_code, MockRequests.DEFAULT_STATUS)
        self.assertEqual(fleet_commander_admin.requests.pop(), "http://%s:8182/session/start" % host)

        ret = self.app.get('/session/stop')
        self.assertEqual(fleet_commander_admin.requests.pop(), "http://%s:8182/session/stop" % host)
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(ret.data, MockRequests.DEFAULT_CONTENT)

    def test_03_stop_start_failed_connection(self):
        fleet_commander_admin.requests.raise_error_on_get()
        rets = [self.app.post('/session/start', data=json.dumps({'host': 'somehost'}), content_type='application/json'),
                self.app.get('/session/stop')]
        for ret in rets:
            self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'could not connect to host'}))
            self.assertEqual(ret.status_code, 403)

    def test_04_change_select_and_deploy(self):
        self.app.post('/session/start', data=json.dumps({'host': 'somehost'}), content_type='application/json')
        fleet_commander_admin.requests.pop()

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
        self.assertEqual(json.dumps(json.loads(ret.data)),
            json.dumps({'org.gnome.gsettings': [[change1['key'], change1['value']], [change2['key'], change2['value']]]}))

        # Select changes for the profile and get UUID to save it
        ret = self.app.post('/changes/select', data=json.dumps({'org.gnome.gsettings': [change2['key'],]}), content_type='application/json')
        self.assertEqual(ret.status_code, 200)

        payload = json.loads(ret.data)
        self.assertTrue(isinstance(payload, dict))
        self.assertTrue('uuid' in payload)
        self.assertTrue('status' in payload)
        self.assertEqual(payload['status'], 'ok')

        # Stop the virtual session
        self.app.get('/session/stop')
        fleet_commander_admin.requests.pop()

        # Save the profile with the selected changes
        uuid = payload['uuid']
        profile_obj = {'profile-name': 'myprofile', 'profile-desc': 'mydesc', 'groups': 'foo,bar', 'users': 'baz'}
        profile_data = json.dumps(profile_obj)
        ret = self.app.post("/profiles/save/"+uuid, content_type='application/json', data=profile_data)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status": "ok"}))
        self.assertEqual(ret.status_code, 200)

        # Get index
        ret = self.app.get("/profiles/")
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([{'url': uuid, 'displayName': profile_obj['profile-name']}]))

        # Get profile
        ret = self.app.get("/profiles/"+uuid)
        self.assertEqual(ret.status_code, 200)
        profile = json.loads(ret.data)
        self.assertTrue(isinstance(profile, dict))
        self.assertEqual(profile['uid'], uuid)
        self.assertEqual(profile['description'], profile_obj['profile-desc'])
        self.assertEqual(profile['name'], profile_obj['profile-name'])
        self.assertEqual(json.dumps(profile['settings']['org.gnome.gsettings'][0]), json.dumps(change2))

        # Get applies
        ret = self.app.get("/profiles/applies")
        self.assertEqual(ret.status_code, 200)
        applies = json.loads(ret.data)
        self.assertTrue(isinstance(applies, dict))
        self.assertTrue(uuid in applies)
        self.assertEqual(json.dumps(applies[uuid]), json.dumps({'groups': ['foo' , 'bar'], 'users': ['baz']}))
        self.assertEqual(len(applies), 1)

        # Remove profile
        ret = self.app.get("/profiles/delete/"+uuid)
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))

        # Check that index is empty
        ret = self.app.get("/profiles/")
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([]))

    def test_05_discard_profile(self):
        host = 'somehost'
        ret = self.app.post('/session/start', data=json.dumps({'host': host}), content_type='application/json')
        fleet_commander_admin.requests.pop()

        # Create profile candidate: We assume all of these methods as tested
        change1 = {'key': '/foo/bar', 'schema': 'foo', 'value': True, 'signature': 'b'}
        self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
        ret = self.app.post('/changes/select', data=json.dumps({'org.gnome.gsettings': [change1['key'],]}), content_type='application/json')
        payload = json.loads(ret.data)

        # discard a profile candidate
        ret = self.app.get('/profiles/discard/' + payload['uuid'])
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))

        # discard a non-existing profile
        ret = self.app.get('/profiles/discard/invaliduuid')
        self.assertEqual(ret.status_code, 403)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'profile invaliduuid not found'}))

        self.app.get('/session/stop')
        fleet_commander_admin.requests.pop()

    def test_06_change_merge_several_changes(self):
        host = 'somehost'
        self.app.post('/session/start', data=json.dumps({'host': host}), content_type='application/json')
        fleet_commander_admin.requests.pop()

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
        fleet_commander_admin.requests.pop()

    def test_07_empty_collector(self):
        host = 'somehost'
        self.app.post('/session/start', data=json.dumps({'host': host}), content_type='application/json')
        fleet_commander_admin.requests.pop()

        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({}))

        self.app.get('/session/stop')
        fleet_commander_admin.requests.pop()

    def test_08_libreoffice_and_gsettings_changes(self):
        host = 'somehost'
        self.app.post('/session/start', data=json.dumps({'host': host}), content_type='application/json')
        fleet_commander_admin.requests.pop ()

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
        self.app.get('/session/stop')
        fleet_commander_admin.requests.pop()

class TestAdminApache(TestAdminWSGIRef):
    test_wsgiref = False

if __name__ == '__main__':
    unittest.main()
