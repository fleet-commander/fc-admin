#!/usr/bin/env python-wrapper.sh
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

from __future__ import absolute_import
import os
import sys
import unittest
import json
import freeipamock

sys.path.append(os.path.join(os.environ["TOPSRCDIR"], "admin"))

from fleetcommander import fcfreeipa

# Mocking assignments
fcfreeipa.api = freeipamock.FreeIPAMock
fcfreeipa.errors = freeipamock.FreeIPAErrors


class TestFreeIPA(unittest.TestCase):

    maxDiff = None

    TEST_PROFILE = {
        "name": "Test Profile",
        "description": "My test profile",
        "priority": 100,
        "settings": {
            "org.freedesktop.NetworkManager": [],
            "org.gnome.gsettings": [
                {
                    "schema": "org.gnome.desktop.notifications.application",
                    "key": "/org/gnome/desktop/notifications/application/abrt-applet/application-id",
                    "value": "'abrt-applet.desktop'",
                    "signature": "s",
                }
            ],
        },
        "users": sorted(
            [
                "guest",
                "admin",
            ]
        ),
        "groups": sorted(
            [
                "admins",
                "editors",
            ]
        ),
        "hosts": sorted(
            [
                "client1",
            ]
        ),
        "hostgroups": sorted(
            [
                "ipaservers",
            ]
        ),
    }

    PROFILE_JSON_DATA = json.dumps(TEST_PROFILE["settings"])

    SAVED_PROFILE_DATA = {
        "cn": (TEST_PROFILE["name"],),
        "description": (TEST_PROFILE["description"],),
        "ipadeskdata": (PROFILE_JSON_DATA,),
    }

    SAVED_PROFILERULE_DATA = {
        "priority": 100,
        "hostcategory": None,
        "users": sorted(["admin", "guest"]),
        "groups": sorted(["admins", "editors"]),
        "hosts": sorted(["client1"]),
        "hostgroups": sorted(["ipaservers"]),
    }

    TEST_PROFILE_MOD = {
        "name": "Test Profile",
        "description": "Test profile modified",
        "priority": 50,
        "settings": {
            "org.freedesktop.NetworkManager": [],
            "org.gnome.gsettings": [
                {
                    "schema": "org.gnome.desktop.notifications.application",
                    "key": "/org/gnome/desktop/notifications/application/abrt-applet/application-id",
                    "value": "'abrt-applet.desktop'",
                    "signature": "s",
                }
            ],
        },
        "users": sorted(
            [
                "admin",
            ]
        ),
        "groups": sorted(
            [
                "admins",
                "editors",
            ]
        ),
        "hosts": sorted(
            [
                "client1",
            ]
        ),
        "hostgroups": sorted(
            [
                "ipaservers",
            ]
        ),
    }

    PROFILE_MOD_JSON_DATA = json.dumps(TEST_PROFILE_MOD["settings"])

    SAVED_PROFILE_DATA_MOD = {
        u"cn": (TEST_PROFILE_MOD["name"],),
        u"description": (TEST_PROFILE_MOD["description"],),
        u"ipadeskdata": (PROFILE_MOD_JSON_DATA,),
    }

    SAVED_PROFILERULE_DATA_MOD = {
        "priority": 50,
        "hostcategory": None,
        "users": sorted(
            [
                "admin",
            ]
        ),
        "groups": sorted(["admins", "editors"]),
        "hosts": sorted(["client1"]),
        "hostgroups": sorted(["ipaservers"]),
    }

    def setUp(self):
        self.ipa = fcfreeipa.FreeIPAConnector()
        freeipamock.FreeIPACommand.data = freeipamock.FreeIPAData()
        self.ipa.connect()

    def test_01_check_user_exists(self):
        # Check existent user
        self.assertTrue(self.ipa.check_user_exists("admin"))
        # Check inexistent user
        self.assertFalse(self.ipa.check_user_exists("fake"))

    def test_02_check_group_exists(self):
        # Check existent group
        self.assertTrue(self.ipa.check_group_exists("admins"))
        # Check inexistent group
        self.assertFalse(self.ipa.check_group_exists("fake"))

    def test_03_check_host_exists(self):
        # Check existent host
        self.assertTrue(self.ipa.check_host_exists("client1"))
        # Check inexistent host
        self.assertFalse(self.ipa.check_host_exists("fake"))

    def test_04_check_hostgroup_exists(self):
        # Check existent hostgroup
        self.assertTrue(self.ipa.check_hostgroup_exists("ipaservers"))
        # Check inexistent hostgroup
        self.assertFalse(self.ipa.check_hostgroup_exists("fake"))

    def test_05_save_profile(self):
        name = self.TEST_PROFILE["name"]
        self.ipa.save_profile(self.TEST_PROFILE)
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profiles, {name: self.SAVED_PROFILE_DATA}
        )
        # Check profile rule
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profilerules,
            {name: self.SAVED_PROFILERULE_DATA},
        )

    def test_06_check_profile_exists(self):
        name = self.TEST_PROFILE["name"]
        # Check non existent profile
        self.assertFalse(self.ipa.check_profile_exists(name))
        # Add profile
        self.ipa.save_profile(self.TEST_PROFILE)
        # Check existent user
        self.assertTrue(self.ipa.check_profile_exists(name))

    def test_07_update_profile(self):
        name = self.TEST_PROFILE["name"]
        self.ipa.save_profile(self.TEST_PROFILE)
        # Save a profile with same UID (overwrite)
        self.ipa.save_profile(self.TEST_PROFILE_MOD)
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profiles,
            {name: self.SAVED_PROFILE_DATA_MOD},
        )
        # Check profile rule
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profilerules,
            {name: self.SAVED_PROFILERULE_DATA_MOD},
        )

    def test_08_del_profile(self):
        # Save a profile
        self.ipa.save_profile(self.TEST_PROFILE)
        # Delete that profile
        self.ipa.del_profile(self.TEST_PROFILE["name"])
        self.assertEqual(freeipamock.FreeIPACommand.data.profiles, {})

    def test_09_get_profiles(self):
        profiles = self.ipa.get_profiles()
        self.assertEqual(profiles, [])
        # Add some profile
        self.ipa.save_profile(self.TEST_PROFILE)
        profiles = self.ipa.get_profiles()
        self.assertEqual(
            profiles,
            [
                (
                    self.TEST_PROFILE["name"],
                    self.TEST_PROFILE["name"],
                    self.TEST_PROFILE["description"],
                )
            ],
        )

    def test_10_get_profile_rule(self):
        self.ipa.save_profile(self.TEST_PROFILE)
        rule = self.ipa.get_profile_rule(self.TEST_PROFILE["name"])
        self.assertEqual(
            rule,
            {
                "memberuser_user": self.TEST_PROFILE["users"],
                "memberuser_group": self.TEST_PROFILE["groups"],
                "memberhost_host": self.TEST_PROFILE["hosts"],
                "memberhost_hostgroup": self.TEST_PROFILE["hostgroups"],
                "ipadeskprofilepriority": (self.TEST_PROFILE["priority"],),
            },
        )

    def test_11_get_profile(self):
        name = self.TEST_PROFILE["name"]
        self.ipa.save_profile(self.TEST_PROFILE)
        profile = self.ipa.get_profile(name)
        self.assertEqual(profile, self.TEST_PROFILE)

    def test_12_get_global_policy(self):
        policy = self.ipa.get_global_policy()
        self.assertEqual(policy, 1)

    def test_13_set_global_policy(self):
        self.ipa.set_global_policy(24)
        self.assertEqual(self.ipa.get_global_policy(), 24)
        # Setting to same value should not throw any exception
        self.ipa.set_global_policy(24)
        # No integer
        with self.assertRaises(freeipamock.FreeIPAErrors.ConversionError):
            self.ipa.set_global_policy("WRONG")
        # Less than 1
        with self.assertRaises(freeipamock.FreeIPAErrors.ValidationError):
            self.ipa.set_global_policy(-1)
        # More than 24
        with self.assertRaises(freeipamock.FreeIPAErrors.ValidationError):
            self.ipa.set_global_policy(25)

    def test_14_hostcategory_setting(self):
        # Adding a profile without hosts sets hostcategory to all
        no_hosts_profile = self.TEST_PROFILE.copy()
        no_hosts_profile["hosts"] = []
        no_hosts_profile["hostgroups"] = []
        self.ipa.save_profile(no_hosts_profile)
        profilerules = freeipamock.FreeIPACommand.data.profilerules
        profiledata = profilerules[self.TEST_PROFILE["name"]]
        self.assertEqual(profiledata["hostcategory"], "all")
        self.ipa.del_profile(self.TEST_PROFILE["name"])
        # Adding a profile with hosts removes hostcategory
        self.ipa.save_profile(self.TEST_PROFILE)
        profiledata = profilerules[self.TEST_PROFILE["name"]]
        self.assertEqual(profiledata["hostcategory"], None)
        # Modifying a profile to have no hosts sets hostcategory to all
        self.ipa.save_profile(no_hosts_profile)
        profiledata = profilerules[self.TEST_PROFILE["name"]]
        self.assertEqual(profiledata["hostcategory"], "all")
        # Modifying a profile with no hosts to have some removes hostcategory
        self.ipa.save_profile(self.TEST_PROFILE)
        profiledata = profilerules[self.TEST_PROFILE["name"]]
        self.assertEqual(profiledata["hostcategory"], None)
        # Modifying a profile with invalid hosts that lead to no hosts
        # sets hostcategory to all
        wrong_hosts_profile = self.TEST_PROFILE.copy()
        wrong_hosts_profile["hosts"] = ["nonexisting"]
        wrong_hosts_profile["hostgroups"] = []
        self.ipa.save_profile(wrong_hosts_profile)
        profiledata = profilerules[self.TEST_PROFILE["name"]]
        self.assertEqual(profiledata["hostcategory"], "all")


if __name__ == "__main__":
    unittest.main()
