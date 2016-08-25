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
# Author: Oliver Gutiérrez <ogutierrez@redhat.com>

import os
import re
import uuid
import json
import logging

from utils import get_data_from_file, test_and_create_file, write_and_close
from database import DBManager


class ProfileNotFoundError(Exception):
    pass


class ProfileDataError(Exception):
    pass


class IndexDataError(Exception):
    pass


class AppliesDataError(Exception):
    pass


class ProfileManager(object):
    """
    Profile management class
    """

    def __init__(self,
                 database_path,
                 profiles_dir):
        """
        Class initialization
        """
        self.PROFILES_DIR = profiles_dir
        self.INDEX_FILE = os.path.join(profiles_dir, 'index.json')
        self.APPLIES_FILE = os.path.join(profiles_dir, 'applies.json')

        # Setup database
        self.db = DBManager(database_path)
        self.profiles = self.db.profiles

    def load_missing_profiles_data(self):
        """
        Load the profile files in profiles directory and adds them to profiles
        database if they do not exist
        """
        filename_re = re.compile(r'^\d+\.json$')
        # Get list of profiles in prodiles directory
        file_list = os.listdir(self.PROFILES_DIR)
        profile_list = []
        for filename in file_list:
            path = os.path.join(self.PROFILES_DIR, filename)
            if os.path.isfile(path) and filename_re.match(filename):
                profile_list.append(filename.split('.')[0])
        # Load applies data
        applies = self.get_applies()
        # Process profiles
        for uid in profile_list:
            # Check if uid is already in database
            if uid not in self.profiles:
                # Read file contents
                path = self.get_profile_path(uid)
                profile = json.loads(get_data_from_file(path))
                profile = self.profile_sanity_check(profile)
                # Append applies data
                if uid in applies:
                    profile.update(applies[uid])
                # Save profile data to database
                self.profiles[uid] = profile

        # Regen main files
        self.update_main_files()

    def get_profile_path(self, uid):
        """
        Get a profile filesystem path by its uid
        Raises an exception if profile does not exist
        """
        filename = '%s.json' % uid
        path = os.path.join(self.PROFILES_DIR, filename)
        return path

    def write_profile_to_disk(self, uid, path=None):
        """
        Writes a profile to disk
        """
        if path is None:
            path = self.get_profile_path(uid)
        profile = self.profiles[uid]

        # Remove profile users and groups information before saving to file
        if 'users' in profile:
            del(profile['users'])
        if 'groups' in profile:
            del(profile['groups'])

        # Save profile to disk
        write_and_close(path, json.dumps(profile))

    def profile_sanity_check(self, profile):
        """
        Perform a sanity check on profile data and return sanitized profile
        """
        if 'uid' not in profile.keys():
            raise ProfileDataError('Profile does not have an UID')

        if not isinstance(profile, dict):
            raise ProfileDataError(
                'Profile object %s is not a dictionary' % uid)

        if profile.get('settings', False):

            if not isinstance(profile['settings'], dict):
                profile['settings'] = {}

            # Gsettings sanity check
            if profile['settings'].get('org.gnome.gsettings', False):
                gsettings = profile['settings']['org.gnome.gsettings']
                if not isinstance(gsettings, list):
                    profile['settings']['org.gnome.gsettings'] = []

            # Gnome Online Accounts sanity check
            if profile['settings'].get('org.gnome.online-accounts', False):
                goa = profile['settings']['org.gnome.online-accounts']
                if not isinstance(goa, dict):
                    profile['settings']['org.gnome.online-accounts'] = {}

            # NetworkManager sanity check
            if profile['settings'].get(
              'org.freedesktop.NetworkManager', False):
                nmdata = profile['settings']['org.freedesktop.NetworkManager']
                if not isinstance(nmdata, list):
                    profile['settings']['org.freedesktop.NetworkManager'] = []

        if not 'users' in profile:
            profile['users'] = []
        if not 'groups' in profile:
            profile['groups'] = []

        return profile

    def update_main_files(self):
        index = []
        applies = {}
        for uid, profile in self.profiles.items():
            # Update index
            index.append({
                'url': '%s.json' % uid,
                'displayName': profile['name']
            })

            # Update applies data
            users = []
            groups = []
            applies[uid] = {
                'users': profile['users'],
                'groups': profile['groups']
            }
        write_and_close(self.INDEX_FILE, json.dumps(index))
        write_and_close(self.APPLIES_FILE, json.dumps(applies))

    def get_profile(self, uid):
        """
        Get a profile data by its uid
        """
        if uid not in self.profiles:
            raise ProfileNotFoundError('Profile %s does not exist' % uid)
        profile = self.profile_sanity_check(self.profiles[uid])
        # del(profile['users'])
        # del(profile['groups'])
        return profile

    def save_profile(self, profile):
        """
        Save a profile with given data
        Path can be specified too, relative to profiles path
        """
        # Generate UID for new profiles
        if 'uid' not in profile:
            profile['uid'] = str(uuid.uuid1().int)

        # Do profile sanity check
        self.profile_sanity_check(profile)
        uid = profile['uid']

        # Save profile data
        self.profiles[uid] = profile

        # Save profile file
        self.write_profile_to_disk(uid)

        # Update index and applies
        self.update_main_files()

        return uid

    def remove_profile(self, uid):
        """
        Remove a profile from profiles data
        """
        if uid in self.profiles:
            del(self.profiles[uid])

        # Remove profile file
        path = self.get_profile_path(uid)
        if os.path.exists(path):
            os.remove(path)

        # Update index and applies
        self.update_main_files()

    def get_index(self):
        """
        Get index data
        """
        test_and_create_file(self.INDEX_FILE, json.dumps([]))
        index = json.loads(get_data_from_file(self.INDEX_FILE))
        if not isinstance(index, list):
            raise IndexDataError(
                '%s does not contain a JSON list as root element' %
                self.INDEX_FILE)
        return index

    def get_applies(self, uid=None):
        """
        Get all applies data or for an specific profile given it's uid
        """
        test_and_create_file(self.APPLIES_FILE, json.dumps({}))
        applies = json.loads(get_data_from_file(self.APPLIES_FILE))
        if not isinstance(applies, dict):
            raise AppliesDataError(
                '%s does not contain a JSON object as root element' %
                self.APPLIES_FILE)
        if uid:
            if uid in applies:
                return applies[uid]
            else:
                raise AppliesDataError(
                    'There is not applies information for given uid: %s' % uid
                )
        return applies
