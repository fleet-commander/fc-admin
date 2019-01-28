# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2018, 2019 Red Hat, Inc.
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
# Authors: Oliver Gutiérrez <ogutierrez@redhat.com>
#          Alberto Ruiz <aruiz@redhat.com>


import os
import logging
import json


class DirectoryData(object):

    def __init__(self, datadir=None):
        self.datadir = datadir
        # Data storage
        self.global_policy = 1
        self.profiles = {}

    def get_json(self):
        data = {
            'policy': self.global_policy,
            'profiles': self.profiles,
        }
        logging.debug('Directory mock data to export: %s' % data)
        jsondata = json.dumps(data)
        logging.debug('Directory mock JSON data to export: %s' % jsondata)
        return jsondata

    def save_to_datadir(self, filename='directorymock-data.json'):
        if self.datadir is not None:
            path = os.path.join(self.datadir, filename)
            logging.debug('Directory mock exporting data to %s' % path)
            with open(path, 'w') as fd:
                fd.write(self.get_json())
                fd.close()
                logging.debug('Directory mock data saved to %s' % path)
        else:
            logging.debug('Directory mock not exporting data (No datadir)')

    # Decorator for exporting data to file
    @classmethod
    def export_data(cls, fun):
        def wrapper(self, *args, **kwargs):
            result = fun(self, *args, **kwargs)
            # Save data storaged in data member
            self.data.save_to_datadir()
            return result
        return wrapper


class DirectoryConnector(object):
    """
    Directory connector module mocking class
    """

    data = None

    def __init__(self, domain=None):
        self._reset_data()

    def _reset_data(self):
        self.data = DirectoryData(datadir=)

    def connect(self, sanity_check=True):
        """
        Connect to AD server
        """
        logging.debug('Directory Mock: Connection')

    def get_global_policy(self):
        return self.GLOBAL_POLICY

    @DirectoryData.export_data
    def set_global_policy(self, policy):
        self.GLOBAL_POLICY = policy

    @DirectoryData.export_data
    def save_profile(self, profile):
        # Check if profile already exists
        cn = profile.get('cn', None)
        if cn is not None:
            # Modifying existing profile
            logging.debug(
                'Directory Mock: Trying to modify profile with cn %s' % cn)
            if cn in self.PROFILES:
                logging.debug(
                    'Directory Mock: Modifying existing profile %s' % cn)
            else:
                logging.debug(
                    'Directory Mock: Profile %s does not exist. Saving.' % cn)
            self.PROFILES[cn] = profile
        else:
            # Saving new profile
            cn = profile['name']
            logging.debug('Directory Mock: Saving new profile. Using name as new id: %s', cn)
            self.profiles[cn] = profile
        return cn

    @DirectoryData.export_data
    def del_profile(self, cn):
        logging.debug('Directory Mock: Deleting profile %s' % cn)
        if cn in self.PROFILES:
            del(self.PROFILES[cn])

    def get_profiles(self):
        logging.debug('Directory Mock: Getting profile list')
        profiles = []
        for cn, profile in self.PROFILES.items():
            profiles.append((
                cn, profile['name'], profile['description']))
        return profiles

    def get_profile(self, cn):
        logging.debug('Directory Mock: Getting profile %s' % cn)
        if cn in self.PROFILES:
            return self.PROFILES[cn]


    # def get_profile_rule(self, name):
    #     pass

    # def get_user(self, username):
    #     base_dn = "CN=Users,%s" % self._get_domain_dn()
    #     filter = '(&(objectclass=user)(CN=%s))' % username
    #     attrs = ['cn', 'objectSid']
    #     resultlist = self.connection.search_s(base_dn, ldap.SCOPE_SUBTREE, filter, attrs)
    #     if len(resultlist) > 0:
    #         data = resultlist[0]
    #         return {
    #             'cn': data[0],
    #             'username': data[1]['cn'][0],
    #             'sid': self.get_sid(data[1]['objectSid'][0])
    #         }
    #     else:
    #         return None

    # def get_group(self, groupname):
    #     base_dn = "%s" % self._get_domain_dn()
    #     filter = '(&(objectclass=group)(CN=%s))' % groupname
    #     attrs = ['cn', 'objectSid']
    #     resultlist = self.connection.search_s(base_dn, ldap.SCOPE_SUBTREE, filter, attrs)
    #     resultlist = [x for x in resultlist if x[0] is not None]
    #     if len(resultlist) > 0:
    #         data = resultlist[0]
    #         return {
    #             'cn': data[0],
    #             'groupname': data[1]['cn'][0],
    #             'sid': self.get_sid(data[1]['objectSid'][0])
    #         }
    #     else:
    #         return None

    # def get_host(self, hostname):
    #     base_dn = "CN=Computers,%s" % self._get_domain_dn()
    #     filter = '(&(objectclass=computer)(CN=%s))' % hostname
    #     attrs = ['cn', 'objectSid']
    #     resultlist = self.connection.search_s(base_dn, ldap.SCOPE_SUBTREE, filter, attrs)
    #     if len(resultlist) > 0:
    #         data = resultlist[0]
    #         return {
    #             'cn': data[0],
    #             'hostname': data[1]['cn'][0],
    #             'sid': self.get_sid(data[1]['objectSid'][0])
    #         }
    #     else:
    #         return None

    # def get_object_by_sid(self, sid):
    #     base_dn = "%s" % self._get_domain_dn()
    #     filter = '(&(|(objectclass=computer)(objectclass=user)(objectclass=group))(objectSid=%s))' % sid
    #     attrs = ['cn', 'objectClass']
    #     resultlist = self.connection.search_s(base_dn, ldap.SCOPE_SUBTREE, filter, attrs)
    #     resultlist = [x for x in resultlist if x[0] is not None]
    #     if len(resultlist) > 0:
    #         data = resultlist[0][1]
    #         return {
    #             'cn': data['cn'][0],
    #             'objectClass': data['objectClass']
    #         }
    #     else:
    #         return None

    # def get_sid(self, sid_ndr):
    #     return ndr_unpack(security.dom_sid, sid_ndr)

    # def get_domain_sid(self):
    #     base_dn = "%s" % self._get_domain_dn()
    #     filter = '(objectClass=*)'
    #     attrs = ['objectSid']
    #     resultlist = self.connection.search_s(base_dn, ldap.SCOPE_BASE, filter, attrs)
    #     return self.get_sid(resultlist[0][1]["objectSid"][0])
