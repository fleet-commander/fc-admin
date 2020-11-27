#!/usr/bin/env python-wrapper.sh
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2019 Red Hat, Inc.
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
from __future__ import absolute_import
import os
import sys
import unittest
import tempfile
import logging
import copy
import json

from ldap import modlist
from ldap import LDAPError

# Samba imports
from samba.ndr import ndr_pack
from samba.dcerpc import security

# Mocking imports
import ldapmock
import smbmock

sys.path.append(os.path.join(os.environ["TOPSRCDIR"], "admin"))

from fleetcommander import fcad

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)

# Mocking assignments
fcad.ldap = ldapmock
fcad.ldap.modlist = modlist
fcad.ldap.LDAPError = LDAPError
fcad.ldap.sasl = ldapmock.sasl


# DNS resolver mock
class DNSResolverMock:
    class DNSResolverResult:
        target = "FC.AD/"

    def query(self, name, querytype):
        return (self.DNSResolverResult,)


fcad.dns.resolver = DNSResolverMock()


# Getpass mock
class GetpassMock:
    def getuser(self):
        return "admin"


fcad.getpass = GetpassMock()

# Samba smblib mock
fcad.libsmb.Conn = smbmock.SMBMock


class TestFCAD(unittest.TestCase):

    maxDiff = None

    DOMAIN = "FC.AD"

    BASE_DOMAIN_DATA = {
        "domain": {
            "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1")),),
            "unpackedObjectSid": "S-1-5-0-0-0-0-1",
        },
        "users": {
            "admin": {
                "cn": ("admin",),
                "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1001")),),
                "unpackedObjectSid": "S-1-5-0-0-0-0-1001",
                "objectClass": ["user"],
            },
            "guest": {
                "cn": ("guest",),
                "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1002")),),
                "unpackedObjectSid": "S-1-5-0-0-0-0-1002",
                "objectClass": ["user"],
            },
        },
        "groups": {
            "admins": {
                "cn": ("admins",),
                "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1011")),),
                "unpackedObjectSid": "S-1-5-0-0-0-0-1011",
                "objectClass": ["group"],
            },
            "editors": {
                "cn": ("editors",),
                "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1012")),),
                "unpackedObjectSid": "S-1-5-0-0-0-0-1012",
                "objectClass": ["group"],
            },
        },
        "hosts": {
            "client1": {
                "cn": ("client1",),
                "objectSid": (ndr_pack(security.dom_sid("S-1-5-0-0-0-0-1101")),),
                "unpackedObjectSid": "S-1-5-0-0-0-0-1101",
                "objectClass": ["computer"],
            },
        },
        "profiles": {},
    }

    GLOBAL_POLICY_TEST_PROFILE = {
        "cn": "",
        "name": fcad.FC_GLOBAL_POLICY_PROFILE_NAME,
        "description": "Global policy profile",
        "priority": 50,
        "settings": {
            "org.freedesktop.FleetCommander": {
                "global_policy": 24,
            },
        },
        "users": [],
        "groups": [],
        "hosts": [],
        "hostgroups": [],
    }

    TEST_PROFILE = {
        "cn": "",
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
        "hostgroups": [],
    }

    TEST_PROFILE_DOM_DATA = {
        "nTSecurityDescriptor": (
            b"\x01\x00\x14\x9c\x14\x00\x00\x000\x00\x00\x00L\x00\x00\x00\xec\x00\x00\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x04\x00\xa0\x00\x03\x00\x00\x00\x07R(\x00 \x00\x04\x00\x02\x00\x00\x00\xc2;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x07Z8\x00 \x00\x00\x00\x03\x00\x00\x00\xbe;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\xa5z\x96\xbf\xe6\r\xd0\x11\xa2\x85\x00\xaa\x000I\xe2\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x07Z8\x00 \x00\x00\x00\x03\x00\x00\x00\xbf;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\xa5z\x96\xbf\xe6\r\xd0\x11\xa2\x85\x00\xaa\x000I\xe2\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\xb8\x02\x12\x00\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xea\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf3\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf4\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00M\x04\x00\x00\x05\x02(\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x01\x00\x00\x00\x00\x00\x05\x0b\x00\x00\x00\x00\x00$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x00\x02\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xea\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf3\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf4\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00M\x04\x00\x00\x00\x02$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x00\x02\x00\x00\x00\x02$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x07\x02\x00\x00\x00\x02\x14\x00\x94\x00\x02\x00\x01\x01\x00\x00\x00\x00\x00\x05\t\x00\x00\x00\x00\x02\x14\x00\x94\x00\x02\x00\x01\x01\x00\x00\x00\x00\x00\x05\x0b\x00\x00\x00\x00\x02\x14\x00\xff\x00\x0f\x00\x01\x01\x00\x00\x00\x00\x00\x05\x12\x00\x00\x00\x00\n\x14\x00\xff\x00\x0f\x00\x01\x01\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00",
        ),
        "displayName": (b"_FC_Test Profile",),
        "cn": None,
        "objectCategory": (
            b"CN=Group-Policy-Container,CN=Schema,CN=Configuration,DC=FC,DC=AD",
        ),
        "objectClass": ([b"top", b"container", b"groupPolicyContainer"],),
        "versionNumber": (b"1",),
        "flags": (b"0",),
        "gPCFileSysPath": (b"\\\\FC.AD\\SysVol\\FC.AD\\Policies\\%s",),
        "description": (b"My test profile",),
    }

    TEST_PROFILE_MOD = {
        "cn": "",
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
        "hostgroups": [],
    }

    TEST_PROFILE_MOD_DOM_DATA = {
        "nTSecurityDescriptor": (
            b"\x01\x00\x14\x9c\x14\x00\x00\x000\x00\x00\x00L\x00\x00\x00\xec\x00\x00\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x04\x00\xa0\x00\x03\x00\x00\x00\x07R(\x00 \x00\x04\x00\x02\x00\x00\x00\xc2;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x07Z8\x00 \x00\x00\x00\x03\x00\x00\x00\xbe;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\xa5z\x96\xbf\xe6\r\xd0\x11\xa2\x85\x00\xaa\x000I\xe2\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x07Z8\x00 \x00\x00\x00\x03\x00\x00\x00\xbf;\x0e\xf3\xf0\x9f\xd1\x11\xb6\x03\x00\x00\xf8\x03g\xc1\xa5z\x96\xbf\xe6\r\xd0\x11\xa2\x85\x00\xaa\x000I\xe2\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\xb8\x02\x12\x00\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xea\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf3\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf4\x03\x00\x00\x05\x028\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00M\x04\x00\x00\x05\x02(\x00\x00\x01\x00\x00\x01\x00\x00\x00\x8f\xfd\xac\xed\xb3\xff\xd1\x11\xb4\x1d\x00\xa0\xc9h\xf99\x01\x01\x00\x00\x00\x00\x00\x05\x0b\x00\x00\x00\x00\x00$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x00\x02\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe9\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xea\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf3\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf4\x03\x00\x00\x00\x02$\x00\x14\x00\x02\x00\x01\x05\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00M\x04\x00\x00\x00\x02$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x00\x02\x00\x00\x00\x02$\x00\xff\x00\x0f\x00\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x04\xa7\x99h\x04@\x89`(d\x08\xb1\x07\x02\x00\x00\x00\x02\x14\x00\x94\x00\x02\x00\x01\x01\x00\x00\x00\x00\x00\x05\t\x00\x00\x00\x00\x02\x14\x00\x94\x00\x02\x00\x01\x01\x00\x00\x00\x00\x00\x05\x0b\x00\x00\x00\x00\x02\x14\x00\xff\x00\x0f\x00\x01\x01\x00\x00\x00\x00\x00\x05\x12\x00\x00\x00\x00\n\x14\x00\xff\x00\x0f\x00\x01\x01\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00",
        ),
        "displayName": (b"_FC_Test Profile",),
        "cn": None,
        "objectCategory": (
            "CN=Group-Policy-Container,CN=Schema,CN=Configuration,DC=FC,DC=AD",
        ),
        "objectClass": (["top", "container", "groupPolicyContainer"],),
        "versionNumber": ("1",),
        "flags": ("0",),
        "gPCFileSysPath": ("\\\\FC.AD\\SysVol\\FC.AD\\Policies\\%s",),
        "description": (b"Test profile modified",),
    }

    def _get_test_profile(self, cn, template=TEST_PROFILE):
        # Returns a copy of the test profile with given cn
        profile = copy.deepcopy(template)
        profile["cn"] = cn
        return profile

    def _get_domain_profile(self, cn):
        key = "CN=%s,CN=Policies,CN=System,DC=FC,DC=AD" % cn
        profile = copy.deepcopy(fcad.ldap.DOMAIN_DATA["profiles"][key])
        return profile

    def _get_domain_profile_data(self, cn, template=TEST_PROFILE_DOM_DATA):
        dom_profile = copy.deepcopy(template)
        dom_profile["cn"] = (cn.encode(),)
        dom_profile["gPCFileSysPath"] = (
            dom_profile["gPCFileSysPath"][0] % cn.encode(),
        )
        return dom_profile

    def _get_cifs_data(self, cn):
        path = os.path.join(
            smbmock.TEMP_DIR, "%s/Policies" % self.DOMAIN, cn, "fleet-commander.json"
        )
        with open(path, "rb") as fd:
            jsondata = fd.read()
            data = json.loads(jsondata)
            fd.close()
            return data

    def setUp(self):
        logging.debug("TESTS: Setting up test environment")
        self.ad = fcad.ADConnector(self.DOMAIN)
        self.ad.connect()
        # Reset domain data for each test
        fcad.ldap.DOMAIN_DATA = copy.deepcopy(self.BASE_DOMAIN_DATA)
        # Reset temporary directory for each new test
        smbmock.TEMP_DIR = tempfile.mkdtemp()

    def test_01_save_profile(self):
        logging.debug("TEST: save_profile")
        cn = self.ad.save_profile(self.TEST_PROFILE)
        # Check saved ldap data is OK
        profile_dom_data = self._get_domain_profile(cn)
        compare_data = self._get_domain_profile_data(cn)
        self.assertEqual(profile_dom_data, compare_data)
        # Check saved samba cifs data is OK
        data = self._get_cifs_data(cn)
        # Check priority
        self.assertEqual(data["priority"], self.TEST_PROFILE["priority"])
        # Check settings
        self.assertEqual(data["settings"], self.TEST_PROFILE["settings"])

    def test_02_get_profiles(self):
        logging.debug("TEST: get_profiles")
        profiles = self.ad.get_profiles()
        self.assertEqual(profiles, [])
        # Add some profile
        cn = self.ad.save_profile(self.TEST_PROFILE)
        profiles = self.ad.get_profiles()
        self.assertEqual(
            profiles,
            [(cn, self.TEST_PROFILE["name"], self.TEST_PROFILE["description"])],
        )

    def test_03_get_profile(self):
        logging.debug("TEST: get_profile")
        cn = self.ad.save_profile(self.TEST_PROFILE)
        profile = self.ad.get_profile(cn)
        test_profile = self._get_test_profile(cn)
        self.assertEqual(profile, test_profile)

    def test_04_update_profile(self):
        logging.debug("TEST: update_profile")
        cn = self.ad.save_profile(self.TEST_PROFILE)
        # Save a profile with same UID (overwrite)
        modified_profile = self._get_test_profile(cn, self.TEST_PROFILE_MOD)
        self.ad.save_profile(modified_profile)
        profile = self.ad.get_profile(cn)
        self.assertEqual(profile, modified_profile)

    def test_05_del_profile(self):
        logging.debug("TEST: del_profile")
        # Save a profile
        cn = self.ad.save_profile(self.TEST_PROFILE)
        self.assertEqual(len(fcad.ldap.DOMAIN_DATA["profiles"].keys()), 1)
        # Delete that profile
        self.ad.del_profile(cn)
        self.assertEqual(fcad.ldap.DOMAIN_DATA["profiles"], {})

    def test_06_get_global_policy(self):
        logging.debug("TEST: set_global_policy")
        # Getting global policy not previously set will return default
        policy = self.ad.get_global_policy()
        self.assertEqual(policy, fcad.FC_GLOBAL_POLICY_DEFAULT)
        # Getting global policy when the global policy is present
        self.ad.save_profile(self.GLOBAL_POLICY_TEST_PROFILE)
        policy = self.ad.get_global_policy()
        self.assertEqual(policy, 24)

    def test_07_set_global_policy(self):
        logging.debug("TEST: set_global_policy")
        # Setting global policy should return previously set value
        self.ad.set_global_policy(22)
        policy = self.ad.get_global_policy()
        self.assertEqual(policy, 22)


if __name__ == "__main__":
    unittest.main()
