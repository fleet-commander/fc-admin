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

    def configure_hypervisor(self):
        return self.app.jsonpost('/hypervisor/', data={
            'host': 'localhost',
            'username': 'testuser',
            'mode': 'session',
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

    def test_01_attempt_save_unselected_profile(self):
        profile_id = '0123456789'
        profile_data = json.dumps(dict(name='myprofile', description='mydesc', settings={}, groups='', users=''))
        ret = self.app.post('/profiles/save/' + profile_id, data=profile_data, content_type='application/json')

        PROFILE = os.path.join(self.args['profiles_dir'], profile_id + '.json')
        self.assertFalse(os.path.exists(PROFILE), msg='profile file was not created')
        self.assertEqual(ret.status_code, 403)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status": "nonexistinguid"}))

    def test_02_hypervisor_configuration(self):
        # Hypervisor nor configured yet
        ret = self.app.get('/hypervisor/')
        self.assertTrue(ret.jsondata['needcfg'])
        self.assertEqual(ret.jsondata['host'], '')
        self.assertEqual(ret.jsondata['username'], '')
        self.assertEqual(ret.jsondata['mode'], 'system')

        # Save hypervisor configuration
        ret = self.configure_hypervisor()

        # Get config again
        ret = self.app.get('/hypervisor/')
        self.assertTrue('needcfg' not in ret.jsondata)
        self.assertEqual(ret.jsondata['host'], 'localhost')
        self.assertEqual(ret.jsondata['username'], 'testuser')
        self.assertEqual(ret.jsondata['mode'], 'session')

    def test_03_start_invalid_data(self):
        ret = self.app.post('/session/start', data=json.dumps({'whatever': 'something'}), content_type='application/json')
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'Invalid data received'}))
        self.assertEqual(ret.status_code, 400)

    def test_04_session_start_stop(self):
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

    def test_05_change_select_and_deploy(self):
        # Setup hipervisor
        self.configure_hypervisor()

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

        # Select changes for the profile and get UUID to save it
        ret = self.app.post('/changes/select', data=json.dumps({'org.gnome.gsettings': [change2['key']]}), content_type='application/json')
        self.assertEqual(ret.status_code, 200)

        payload = json.loads(ret.data)
        self.assertTrue(isinstance(payload, dict))
        self.assertTrue('uuid' in payload)
        self.assertTrue('status' in payload)
        self.assertEqual(payload['status'], 'ok')

        # Stop the virtual session
        self.app.get('/session/stop')

        # Save the profile with the selected changes
        uuid = payload['uuid']
        profile_obj = {'profile-name': 'myprofile', 'profile-desc': 'mydesc', 'groups': 'foo,bar', 'users': 'baz'}
        profile_data = json.dumps(profile_obj)
        ret = self.app.post("/profiles/save/"+uuid, content_type='application/json', data=profile_data)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status": "ok"}))
        self.assertEqual(ret.status_code, 200)

        # Get index
        ret = self.app.get("/profiles/")
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([{'url': uuid + ".json", 'displayName': profile_obj['profile-name']}]))

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

    def test_06_discard_profile(self):
        # Setup hipervisor
        self.configure_hypervisor()

        # Start session
        data = {'domain': 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81', 'admin_host': 'localhost', 'admin_port': 8181}
        ret = self.app.jsonpost('/session/start', data=data)
        print ret.data

        # Create profile candidate: We assume all of these methods as tested
        change1 = {'key': '/foo/bar', 'schema': 'foo', 'value': True, 'signature': 'b'}
        self.app.post('/changes/submit/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
        ret = self.app.post('/changes/select', data=json.dumps({'org.gnome.gsettings': [change1['key']]}), content_type='application/json')

        # discard a profile candidate
        ret = self.app.get('/profiles/discard/' + ret.jsondata['uuid'])
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps({"status": "ok"}), json.dumps(ret.jsondata))

        # discard a non-existing profile
        ret = self.app.get('/profiles/discard/invaliduuid')
        self.assertEqual(ret.status_code, 403)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'profile invaliduuid not found'}))

        self.app.get('/session/stop')

    def test_07_change_merge_several_changes(self):

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

    def test_08_empty_collector(self):

        ret = self.app.get('/changes')
        self.assertEqual(ret.status_code, 200)
        self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({}))

    def test_09_libreoffice_and_gsettings_changes(self):

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


class TestAdminApache(TestAdminWSGIRef):
    test_wsgiref = False

if __name__ == '__main__':
    unittest.main()
