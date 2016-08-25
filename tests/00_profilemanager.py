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
import copy
import tempfile
import shutil
import unittest
import json

sys.path.append(os.path.join(os.environ['TOPSRCDIR'], 'admin'))
sys.path.append(os.path.join(
    os.environ['TOPSRCDIR'], '_build/sub/admin/fleetcommander'))

from fleetcommander import profiles


class TestProfileManager(unittest.TestCase):

    DUMMY_PROFILE = {
       u'description': u'Dummy profile for testing purproses',
       u'name': u'Dummy profile',
       u'settings': {
          u'org.freedesktop.NetworkManager': [],
          u'org.gnome.gsettings': [
             {
                u'key': u'/org/gnome/software/popular-overrides',
                u'value': [
                   u'app1.desktop',
                   u'app2.desktop'
                ],
                u'signature': u'as'
             },
             {
                u'signature': u's',
                u'value': u'mtime',
                u'key': u'/org/gnome/nautilus/preferences/default-sort-order',
                u'schema': u'org.gnome.nautilus.preferences'
             },
          ],
          u'org.libreoffice.registry': [],
          u'org.gnome.online-accounts': {
             u'Account account_fc_1469708725_0': {
                u'DocumentsEnabled': False,
                u'MailEnabled': True,
                u'Provider': u'windows_live'
             }
          }
       },
       u'users': [u'user1', u'user2'],
       u'groups': [u'group1', u'group2'],
    }

    def setUp(self):
        self.test_directory = tempfile.mkdtemp(prefix='fc-profilemanager-test')
        profiles_dir = os.path.join(self.test_directory, 'profiles')
        self.profiles = profiles.ProfileManager(
            database_path=os.path.join(self.test_directory, 'database.db'),
            profiles_dir=profiles_dir)
        os.mkdir(profiles_dir)

    def tearDown(self):
        # Remove test directory
        shutil.rmtree(self.test_directory)

    def get_dummy_profile(self):
        return copy.deepcopy(self.DUMMY_PROFILE)

    def test_00_get_profile_path(self):
        path = self.profiles.get_profile_path('SOMEUID')
        self.assertEqual(
            path, os.path.join(self.profiles.PROFILES_DIR, 'SOMEUID.json'))

    def test_01_profile_sanity_check(self):
        profile_data = self.get_dummy_profile()

        # Profile without uid should raise ProfileDataError
        with self.assertRaisesRegexp(
          profiles.ProfileDataError,
          'Profile does not have an UID'):
            self.profiles.profile_sanity_check(profile_data)

        profile_data['uid'] = 'someuid'

        # Check profile with wrong gsettings
        profile_data['settings']['org.gnome.gsettings'] = 'WRONG'
        self.profiles.profile_sanity_check(profile_data)
        self.assertEqual(profile_data['settings']['org.gnome.gsettings'], [])

        # Check profile with wrong gnome online accounts data
        profile_data['settings']['org.gnome.online-accounts'] = 'WRONG'
        self.profiles.profile_sanity_check(profile_data)
        self.assertEqual(
            profile_data['settings']['org.gnome.online-accounts'], {})

        # Check profile with wrong gnome online accounts data
        profile_data['settings']['org.freedesktop.NetworkManager'] = 'WRONG'
        self.profiles.profile_sanity_check(profile_data)
        self.assertEqual(
            profile_data['settings']['org.freedesktop.NetworkManager'], [])

        # Check profile with no settings
        profile_data['settings'] = 'WRONG'
        self.profiles.profile_sanity_check(profile_data)
        self.assertEqual(profile_data['settings'], {})

    def test_02_save_new_profile(self):
        # Save a completely new profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)
        profile_data['uid'] = uid

        # Check profile has been saved
        self.assertEqual(
            self.profiles.profiles[uid],
            profile_data)

        # Check profile is saved to disk
        path = self.profiles.get_profile_path(uid)
        del(profile_data['users'])
        del(profile_data['groups'])
        with open(path, 'r') as fd:
            saved_data = json.loads(fd.read())
            self.assertEqual(
                profile_data, saved_data)
            fd.close()

        # Check index has been updated as well
        with open(self.profiles.INDEX_FILE, 'r') as fd:
            index_data = json.loads(fd.read())
            elem = None
            jsonurl = '%s.json' % uid
            for x in index_data:
                if x['url'] == jsonurl:
                    elem = x
                    break

            self.assertTrue(elem is not None)
            self.assertEqual(elem, {
                'url': '%s.json' % profile_data['uid'],
                'displayName': 'Dummy profile',
            })
            fd.close()

        # Check applies has been updated too
        with open(self.profiles.APPLIES_FILE, 'r') as fd:
            applies_data = json.loads(fd.read())
            self.assertTrue(uid in applies_data)
            self.assertEqual(applies_data[uid], {
               'users': ['user1', 'user2'],
               'groups': ['group1', 'group2'],
            })
            fd.close()

    def test_02_update_existent_profile(self):
        # Add new profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)
        profile_data['uid'] = uid

        # Change profile data
        profile_data['name'] = 'Another dummy profile'
        profile_data['users'] = ['otheruser1', 'anotheruser2']
        profile_data['groups'] = ['othergroup1', 'anothergroup2']

        updated_uid = self.profiles.save_profile(profile_data)

        self.assertEqual(uid, updated_uid)

        # Check profile is updated into disk
        path = self.profiles.get_profile_path(uid)
        del(profile_data['users'])
        del(profile_data['groups'])
        with open(path, 'r') as fd:
            saved_data = json.loads(fd.read())
            self.assertEqual(
                profile_data, saved_data)
            fd.close()

        # Check index has been updated as well
        with open(self.profiles.INDEX_FILE, 'r') as fd:
            index_data = json.loads(fd.read())
            elem = None
            jsonurl = '%s.json' % uid
            for x in index_data:
                if x['url'] == jsonurl:
                    elem = x
                    break

            self.assertTrue(elem is not None)
            self.assertEqual(elem, {
                'url': '%s.json' % profile_data['uid'],
                'displayName': 'Another dummy profile',
            })
            fd.close()

        # Check applies has been updated too
        with open(self.profiles.APPLIES_FILE, 'r') as fd:
            applies_data = json.loads(fd.read())
            self.assertTrue(uid in applies_data)
            self.assertEqual(applies_data[uid], {
               'users': ['otheruser1', 'anotheruser2'],
               'groups': ['othergroup1', 'anothergroup2'],
            })
            fd.close()

    def test_04_get_profile(self):
        # Try to get an inexistent profile
        self.assertRaises(
            profiles.ProfileNotFoundError,
            self.profiles.get_profile, 'wrong uid')

        # Add a profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)
        profile_data['uid'] = uid

        # Obtain it again
        self.assertEqual(
            profile_data,
            self.profiles.get_profile(uid)
        )

    def test_05_remove_profile(self):
        # Add new profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)

        # Now delete it
        self.profiles.remove_profile(uid)

        # Check UID is not in profiles data
        self.assertTrue(uid not in self.profiles.profiles)

        # Check profile file has been removed
        path = self.profiles.get_profile_path(uid)
        self.assertFalse(os.path.exists(path))

    def test_06_get_index(self):
        # Add new profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)

        # Get index data
        index = self.profiles.get_index()
        self.assertEqual(index, [{
            'url': '%s.json' % uid,
            'displayName': 'Dummy profile',
        }])

    def test_07_get_applies(self):
        # Add new profile
        profile_data = self.get_dummy_profile()
        uid = self.profiles.save_profile(profile_data)

        # Get index data
        applies = self.profiles.get_applies()
        self.assertEqual(applies, {
            uid: {
               'users': ['user1', 'user2'],
               'groups': ['group1', 'group2'],
            }
        })

    def test_08_load_missing_profiles_data(self):
        # Add profile two different profiles
        profile_data = self.get_dummy_profile()
        profile_data['name'] = 'Profile 1'
        uid1 = self.profiles.save_profile(profile_data)

        profile_data = self.get_dummy_profile()
        profile_data['name'] = 'Profile 2'
        uid2 = self.profiles.save_profile(profile_data)

        # Remove them from database only
        del(self.profiles.profiles[uid1])
        del(self.profiles.profiles[uid2])

        # Check that profiles are not in database
        self.assertRaises(
            profiles.ProfileNotFoundError, self.profiles.get_profile, uid1)
        self.assertRaises(
            profiles.ProfileNotFoundError, self.profiles.get_profile, uid2)

        # Check files are written
        self.assertTrue(os.path.isfile(self.profiles.get_profile_path(uid1)))
        self.assertTrue(os.path.isfile(self.profiles.get_profile_path(uid2)))

        # Import missing data
        self.profiles.load_missing_profiles_data()

        # Check index
        index = self.profiles.get_index()
        index.sort()
        self.assertEqual(index, [
            {
                'url': '%s.json' % uid1,
                'displayName': 'Profile 1',
            },
            {
                'url': '%s.json' % uid2,
                'displayName': 'Profile 2',
            },
        ])

        # Check applies
        self.assertEqual(self.profiles.get_applies(), {
            uid1: {
               'users': ['user1', 'user2'],
               'groups': ['group1', 'group2'],
            },
            uid2: {
               'users': ['user1', 'user2'],
               'groups': ['group1', 'group2'],
            }
        })

if __name__ == '__main__':
    unittest.main()
