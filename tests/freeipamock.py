#!/usr/bin/env python2
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
import logging
import json
import base64

class FreeIPAData(object):

    def __init__(self, datadir=None):
        self.datadir = datadir
        # Data storage
        self.users = ['admin', 'guest', ]
        self.groups = ['admins', 'editors', ]
        self.hosts = ['client1', ]
        self.hostgroups = ['ipaservers', ]
        self.profiles = {}
        self.profilerules = {}
        self.global_policy = 1

    def get_json(self):
        return json.dumps({
            'users': self.users,
            'groups': self.groups,
            'hosts': self.hosts,
            'hostgroups': self.hostgroups,
            'profiles': self.profiles,
            'profilerules': self.profilerules,
            'global_policy': self.global_policy,
        })

    def save_to_datadir(self, filename='freeipamock-data.json'):
        if self.datadir is not None:
            path = os.path.join(self.datadir, filename)
            with open(path, 'wb') as fd:
                fd.write(self.get_json())
                fd.close()
                logging.debug('FreeIPA mock data saved to %s' % path)

    # Decorator for exporting data to file
    @classmethod
    def export_data(cls, fun):
        def wrapper(self, *args, **kwargs):
            result = fun(self, *args, **kwargs)
            # Save data storaged in data member
            self.data.save_to_datadir()
            return result
        return wrapper


class FreeIPAErrors(object):

    class NotFound(Exception):
        pass

    class EmptyModlist(Exception):
        pass

    class DuplicateEntry(Exception):
        pass

    class ConversionError(Exception):
        pass

    class ValidationError(Exception):
        pass


class FreeIPARPCClient(object):

    @staticmethod
    def isconnected():
        return True

    @staticmethod
    def connect():
        logging.debug('Mocking IPA connection')
        return


class FreeIPABackend(object):
    rpcclient = FreeIPARPCClient


class FreeIPACommand(object):

    data = None

    def ping(self):
        return

    def deskprofileconfig_show(self):
        return {
            'result': {
                'ipadeskprofilepriority': (unicode(self.data.global_policy),)
            }
        }

    @FreeIPAData.export_data
    def deskprofileconfig_mod(self, ipadeskprofilepriority):
        if type(ipadeskprofilepriority) is not int:
            raise FreeIPAErrors.ConversionError(
                "invalid 'priority': must be an integer")
        else:
            if ipadeskprofilepriority == self.data.global_policy:
                raise FreeIPAErrors.EmptyModlist(
                    "no modifications to be performed")
            if ipadeskprofilepriority < 1:
                raise FreeIPAErrors.ValidationError(
                    "invalid 'priority': must be at least 1")
            if ipadeskprofilepriority > 24:
                raise FreeIPAErrors.ValidationError(
                    "invalid 'priority': can be at most 24")
        self.data.global_policy = ipadeskprofilepriority

    def user_show(self, user):
        if user in self.data.users:
            return {
                u'result': {},
                u'value': unicode(user),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def group_show(self, group):
        if group in self.data.groups:
            return {
                u'result': {},
                u'value': unicode(group),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def host_find(self, sizelimit):
        count = len(self.data.hosts)
        result = []
        for host in self.data.hosts:
            result.append({
                'fqdn': (host,)
            })
        res = {
            u'count': count,
            u'summary': u'%s Hosts matched' % count,
            u'result': tuple(result),
            u'truncated': False
        }
        return res

    def host_show(self, host):
        if host in self.data.hosts:
            return {
                u'result': {},
                u'value': unicode(host),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def hostgroup_add(self, hostgroup):
        if hostgroup in self.data.hostgroups:
            raise DuplicateEntry('Hostgroup "%s" already exists' % hostgroup)
        else:
            self.data.hostgroups.append(hostgroup)

    def hostgroup_show(self, hostgroup):
        if hostgroup in self.data.hostgroups:
            return {
                u'result': {},
                u'value': unicode(hostgroup),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def hostgroup_add_member(self, hostgroup, host):
        pass

    def automember_add(self, name, type):
        pass

    def automember_del(self, name, type):
        pass

    def automember_add_condition(self, name, type, key, automemberinclusiveregex):
        pass

    def automember_remove_condition(self, name, type, key):
        pass

    @FreeIPAData.export_data
    def deskprofile_add(self, name, description, ipadeskdata):
        if name in self.data.profiles:
            raise FreeIPAErrors.DuplicateEntry()
        else:
            self.data.profiles[name] = {
                u'cn': (unicode(name),),
                u'description': (unicode(description),),
                u'ipadeskdata': (unicode(ipadeskdata),),
            }

    @FreeIPAData.export_data
    def deskprofile_mod(self, cn, description, ipadeskdata):
        if cn in self.data.profiles:
            self.data.profiles[cn]['description'] = (unicode(description),)
            self.data.profiles[cn]['ipadeskdata'] = (unicode(ipadeskdata),)
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofilerule_add(self, name,
                            ipadeskprofiletarget, ipadeskprofilepriority,
                            hostcategory=None):
        if name in self.data.profilerules:
            raise FreeIPAErrors.DuplicateEntry()
        else:
            logging.debug(
                'IPAMock: profile rule for %s' % name)
            self.data.profilerules[name] = {
                'priority': ipadeskprofilepriority,
                'hostcategory': hostcategory,
                'users': [],
                'groups': [],
                'hosts': [],
                'hostgroups': [],
            }

    @FreeIPAData.export_data
    def deskprofilerule_add_user(self, name, user, group):
        logging.debug(
            'IPAMock: Adding users and groups to rule %s, %s, %s' % (name, user, group))
        if name in self.data.profilerules:
            logging.debug(
                'IPAMock: profile rule data before adding user/group data for %s: %s' % (
                    name, self.data.profilerules[name]))
            user = list(set(user).intersection(set(self.data.users)))
            self.data.profilerules[name]['users'].extend(user)
            self.data.profilerules[name]['users'] = list(
                set(self.data.profilerules[name]['users']))
            group = list(set(group).intersection(set(self.data.groups)))
            self.data.profilerules[name]['groups'].extend(group)
            self.data.profilerules[name]['groups'] = list(
                set(self.data.profilerules[name]['groups']))
            logging.debug(
                'IPAMock: profile rule data after adding user/group data for %s: %s' % (
                    name, self.data.profilerules[name]))
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofilerule_add_host(self, name, host, hostgroup):
        if name in self.data.profilerules:
            logging.debug(
                'IPAMock: Adding hosts and hostgroups to rule %s, %s, %s' % (name, host, hostgroup))
            host = list(set(host).intersection(set(self.data.hosts)))
            self.data.profilerules[name]['hosts'].extend(host)
            self.data.profilerules[name]['hosts'] = list(
                set(self.data.profilerules[name]['hosts']))
            hostgroup = list(set(hostgroup).intersection(set(self.data.hostgroups)))
            self.data.profilerules[name]['hostgroups'].extend(hostgroup)
            self.data.profilerules[name]['hostgroups'] = list(
                set(self.data.profilerules[name]['hostgroups']))
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofilerule_remove_user(self, name, user, group):
        if name in self.data.profilerules:
            users = set(self.data.profilerules[name]['users']) - set(user)
            self.data.profilerules[name]['users'] = list(users)
            groups = set(self.data.profilerules[name]['groups']) - set(group)
            self.data.profilerules[name]['groups'] = list(groups)
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofilerule_remove_host(self, name, host, hostgroup):
        if name in self.data.profilerules:
            hosts = set(self.data.profilerules[name]['hosts']) - set(host)
            self.data.profilerules[name]['hosts'] = list(hosts)
            hostgroups = set(
                self.data.profilerules[name]['hostgroups']) - set(hostgroup)
            self.data.profilerules[name]['hostgroups'] = list(hostgroups)
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofile_del(self, name):
        if name in self.data.profiles:
            del(self.data.profiles[name])

    @FreeIPAData.export_data
    def deskprofilerule_del(self, name):
        if name in self.data.profilerules:
            del(self.data.profilerules[name])
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_find(self, criteria, sizelimit, all):
        count = len(self.data.profiles.keys())
        res = {
            u'count': count,
            u'summary': u'%s Desktop Profiles matched' % count,
            u'result': tuple(self.data.profiles.values()),
            u'truncated': False
        }
        return res

    def deskprofile_show(self, name, all):
        if name in self.data.profiles:
            profile = self.data.profiles[name].copy()
            profile['ipadeskdata'] = (base64.b64decode(profile['ipadeskdata'][0]),)
            return {'result': profile}
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_show(self, name, all):
        if name in self.data.profilerules:
            return {
                'result': {
                    'memberuser_user': sorted(
                        self.data.profilerules[name]['users']),
                    'memberuser_group': sorted(
                        self.data.profilerules[name]['groups']),
                    'memberhost_host': sorted(
                        self.data.profilerules[name]['hosts']),
                    'memberhost_hostgroup': sorted(
                        self.data.profilerules[name]['hostgroups']),
                    'ipadeskprofilepriority': (
                        self.data.profilerules[name]['priority'],),
                }
            }
        else:
            raise FreeIPAErrors.NotFound()

    @FreeIPAData.export_data
    def deskprofilerule_mod(self, cn,
                            ipadeskprofiletarget, ipadeskprofilepriority,
                            hostcategory=None):
        if cn in self.data.profilerules:
            self.data.profilerules[cn]['priority'] = ipadeskprofilepriority
            self.data.profilerules[cn]['hostcategory'] = hostcategory
        else:
            raise FreeIPAErrors.NotFound()


class FreeIPAMock(object):

    Backend = FreeIPABackend
    Command = FreeIPACommand()
    _connected = False

    @staticmethod
    def connect():
        FreeIPAMock._connected = True

    @staticmethod
    def is_connected():
        return FreeIPAMock._connected

    @staticmethod
    def isdone(parm):
        return True

    @staticmethod
    def bootstrap(context, log):
        return

    @staticmethod
    def finalize():
        return
