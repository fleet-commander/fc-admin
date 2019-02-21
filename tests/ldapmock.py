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
import logging

# LDAP imports
from ldap import modlist
from ldap import LDAPError


DOMAIN_DATA = None


class SASLMock(object):

    @staticmethod
    def sasl(cb_value_dict, mech):
        # We asume auth is OK as long as mechanism is GSSAPI
        # We ignore callbacks
        if mech == 'GSSAPI':
            return 'AUTH OK'
        raise Exception('SASLMock: Auth mechanism is not GSSAPI (Kerberos)')


class LDAPConnectionMock(object):

    protocol_version = 3

    def __init__(self, server_address):
        logging.debug('LDAPMock initializing connection: %s' % server_address)
        self.server_address = server_address
        self.options = {}
        self._domain_data = DOMAIN_DATA

    def _ldif_to_ldap_data(self, ldif):
        data = {}
        for elem in ldif:
            data[elem[0]] = (elem[1], )
        return data

    def set_option(self, key, value):
        self.options[key] = value

    def sasl_interactive_bind_s(self, who, sasl_auth):
        # We assume auth is ok if who is '' and sasl_auth was created using sasl
        if who == '' and sasl_auth == 'AUTH OK':
            return
        raise Exception(
            'SASLMock: Incorrect parameters for SASL binding: %s, %s' % (
                who, sasl_auth))

    def search_s(
            self, base, scope, filterstr='(objectClass=*)', attrlist=None,
            attrsonly=0, timeout=-1):
        logging.debug('LDAPMock search_s: %s - %s' % (base, filterstr))
        if base == 'DC=FC,DC=AD':
            groupfilter = '(&(objectclass=group)(CN='
            sidfilter = '(&(|(objectclass=computer)(objectclass=user)(objectclass=group))(objectSid='
            if filterstr == '(objectClass=*)' and attrlist == ['objectSid']:
                    return (
                        ('cn', self._domain_data['domain']),
                    )
            elif sidfilter in filterstr:
                filtersid = filterstr[len(sidfilter):-2]
                for objclass in ['users', 'groups', 'hosts']:
                    for key, elem in self._domain_data[objclass].items():
                        # Use unpacked object sid to avoid use of ndr_unpack
                        if filtersid == elem['unpackedObjectSid']:
                            return [(elem['cn'], elem), ]
            elif groupfilter in filterstr:
                groupname = filterstr[len(groupfilter):-2]
                if groupname in self._domain_data['groups'].keys():
                    return (
                        ('cn', self._domain_data['groups'][groupname]),
                    )
        elif base == 'CN=Users,DC=FC,DC=AD':
            userfilter = '(&(objectclass=user)(CN='
            if userfilter in filterstr:
                username = filterstr[len(userfilter):-2]
                if username in self._domain_data['users'].keys():
                    return (
                        ('cn', self._domain_data['users'][username]),
                    )
        elif base == 'CN=Computers,DC=FC,DC=AD':
            hostfilter = '(&(objectclass=computer)(CN='
            if hostfilter in filterstr:
                hostname = filterstr[len(hostfilter):-2]
                if hostname in self._domain_data['hosts'].keys():
                    return (
                        ('cn', self._domain_data['hosts'][hostname]),
                    )
        elif base == 'CN=Policies,CN=System,DC=FC,DC=AD':
            if filterstr == '(objectclass=groupPolicyContainer)':
                profile_list = []
                for cn, profile in self._domain_data['profiles'].items():
                    profile_list.append((cn, self._domain_data['profiles'][cn]))
                return profile_list
            elif '(displayName=' in filterstr:
                displayname = filterstr[len('(displayName='):-1]
                # Trying to get a profile by its display name
                for key, elem in self._domain_data['profiles'].items():
                    if elem['displayName'][0].decode() == displayname:
                        return [(elem['cn'], elem)]
            else:
                cn = 'CN=%s,CN=Policies,CN=System,DC=FC,DC=AD' % filterstr[4:-1]
                if cn in self._domain_data['profiles'].keys():
                    return [(cn, self._domain_data['profiles'][cn])]
        return []

    def add_s(self, dn, ldif):
        self._domain_data['profiles'][dn] = self._ldif_to_ldap_data(ldif)

    def modify_s(self, dn, ldif):
        profile = self._domain_data['profiles'][dn]
        for dif in ldif:
            value = (dif[2], )
            if dif[1] in ['displayName', 'description']:
                value = (dif[2], )
            profile[dif[1]] = value

    def delete_s(self, dn):
        logging.debug('LDAPMock: delete_s %s' % dn)
        if dn in self._domain_data['profiles'].keys():
            del(self._domain_data['profiles'][dn])


# Mock sasl module
sasl = SASLMock


# Constants
OPT_REFERRALS = 1
SCOPE_SUBTREE = 2
SCOPE_BASE = 3
MOD_REPLACE = 4


# Functions
def initialize(server_address):
    return LDAPConnectionMock(server_address)
