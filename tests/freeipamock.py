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


class FreeIPAData(object):

    def __init__(self):
        self.users = ['admin', 'guest', ]
        self.groups = ['admins', 'editors', ]
        self.hosts = ['client1', ]
        self.hostgroups = ['ipaservers', ]
        self.profiles = {}
        self.profilerules = {}


class FreeIPAErrors(object):

    class NotFound(Exception):
        pass

    class EmptyModlist(Exception):
        pass

    class DuplicateEntry(Exception):
        pass


class FreeIPARPCClient(object):

    @staticmethod
    def isconnected():
        return True

    @staticmethod
    def connect():
        return


class FreeIPABackend(object):
    rpcclient = FreeIPARPCClient


class FreeIPACommand(object):

    data = None

    def ping(self):
        return

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

    def host_show(self, host):
        if host in self.data.hosts:
            return {
                u'result': {},
                u'value': unicode(host),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def hostgroup_show(self, hostgroup):
        if hostgroup in self.data.hostgroups:
            return {
                u'result': {},
                u'value': unicode(hostgroup),
                u'summary': None
            }
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_add(self, name, description, ipadeskdata):
        if name in self.data.profiles:
            raise FreeIPAErrors.DuplicateEntry()
        else:
            self.data.profiles[name] = {
                u'cn': (unicode(name),),
                u'description': (unicode(description),),
                u'ipadeskdata': (unicode(ipadeskdata),),
            }

    def deskprofile_mod(self, name, description, ipadeskdata):
        if name in self.data.profiles:
            self.data.profiles[name]['description'] = (unicode(description),)
            self.data.profiles[name]['ipadeskdata'] = (unicode(ipadeskdata),)
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_add(self, name,
                            ipadeskprofiletarget, ipadeskprofilepriority):
        if name in self.data.profilerules:
            raise FreeIPAErrors.DuplicateEntry()
        else:
            self.data.profilerules[name] = {
                'priority': ipadeskprofilepriority,
                'users': [],
                'groups': [],
                'hosts': [],
                'hostgroups': [],
            }

    def deskprofilerule_add_user(self, name, user, group):
        if name in self.data.profilerules:
            self.data.profilerules[name]['users'].extend(user)
            self.data.profilerules[name]['users'] = list(
                set(self.data.profilerules[name]['users']))
            self.data.profilerules[name]['groups'].extend(group)
            self.data.profilerules[name]['groups'] = list(
                set(self.data.profilerules[name]['groups']))
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_add_host(self, name, host, hostgroup):
        if name in self.data.profilerules:
            self.data.profilerules[name]['hosts'].extend(host)
            self.data.profilerules[name]['hosts'] = list(
                set(self.data.profilerules[name]['hosts']))
            self.data.profilerules[name]['hostgroups'].extend(hostgroup)
            self.data.profilerules[name]['hostgroups'] = list(
                set(self.data.profilerules[name]['hostgroups']))
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_remove_user(self, name, user, group):
        if name in self.data.profilerules:
            users = set(self.data.profilerules[name]['users']) - set(user)
            self.data.profilerules[name]['users'] = list(users)
            groups = set(self.data.profilerules[name]['groups']) - set(group)
            self.data.profilerules[name]['groups'] = list(groups)
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_remove_host(self, name, host, hostgroup):
        if name in self.data.profilerules:
            hosts = set(self.data.profilerules[name]['hosts']) - set(host)
            self.data.profilerules[name]['hosts'] = list(hosts)
            hostgroups = set(
                self.data.profilerules[name]['hostgroups']) - set(hostgroup)
            self.data.profilerules[name]['hostgroups'] = list(hostgroups)
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_del(self, name):
        if name in self.data.profiles:
            del(self.data.profiles[name])

    def deskprofilerule_del(self, name):
        if name in self.data.profilerules:
            del(self.data.profilerules[name])
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_find(self, criteria, all):
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
            return {'result': self.data.profiles[name]}
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

    def deskprofilerule_mod(self, name,
                            ipadeskprofiletarget, ipadeskprofilepriority):
        if name in self.data.profilerules:
            self.data.profilerules[name]['priority'] = ipadeskprofilepriority
        else:
            raise FreeIPAErrors.NotFound()


class FreeIPAMock(object):

    Backend = FreeIPABackend
    Command = FreeIPACommand()

    @staticmethod
    def isdone(parm):
        return True

    @staticmethod
    def bootstrap(context, log):
        return

    @staticmethod
    def finalize():
        return
