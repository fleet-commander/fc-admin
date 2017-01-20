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

    def deskprofile_mod(self, uid, newuid):
        if uid in self.data.profiles:
            self.data.profiles[newuid] = {
                u'cn': (unicode(newuid),),
            }
            del(self.data.profiles[uid])
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_add(self, uid, description, ipadeskdata):
        self.data.profiles[uid] = {
            u'cn': (unicode(uid),),
            u'description': (unicode(description),),
            u'ipadeskdata': (unicode(ipadeskdata),),
        }

    def deskprofilerule_add(self, uid,
                            ipadeskprofiletarget, ipadeskprofilepriority):
        self.data.profilerules[uid] = {
            'priority': ipadeskprofilepriority,
            'users': [],
            'groups': [],
            'hosts': [],
            'hostgroups': [],
        }

    def deskprofilerule_add_user(self, uid, user, group):
        if uid in self.data.profilerules:
            self.data.profilerules[uid]['users'].extend(user)
            self.data.profilerules[uid]['users'] = list(set(self.data.profilerules[uid]['users']))
            self.data.profilerules[uid]['groups'].extend(group)
            self.data.profilerules[uid]['groups'] = list(set(self.data.profilerules[uid]['groups']))
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_add_host(self, uid, host, hostgroup):
        if uid in self.data.profilerules:
            self.data.profilerules[uid]['hosts'].extend(host)
            self.data.profilerules[uid]['hosts'] = list(set(self.data.profilerules[uid]['hosts']))
            self.data.profilerules[uid]['hostgroups'].extend(hostgroup)
            self.data.profilerules[uid]['hostgroups'] = list(set(self.data.profilerules[uid]['hostgroups']))
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofile_del(self, uid):
        if uid in self.data.profiles:
            del(self.data.profiles[uid])

    def deskprofilerule_del(self, uid):
        if uid in self.data.profilerules:
            del(self.data.profilerules[uid])
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

    def deskprofile_show(self, uid, all):
        if uid in self.data.profiles:
            return {'result': self.data.profiles[uid]}
        else:
            raise FreeIPAErrors.NotFound()

    def deskprofilerule_show(self, uid, all):
        if uid in self.data.profilerules:
            return {
                'result': {
                    'memberuser_user': sorted(self.data.profilerules[uid]['users']),
                    'memberuser_group': sorted(self.data.profilerules[uid]['groups']),
                    'memberhost_host': sorted(self.data.profilerules[uid]['hosts']),
                    'memberhost_hostgroup': sorted(self.data.profilerules[uid]['hostgroups']),
                    'ipadeskprofilepriority': (self.data.profilerules[uid]['priority'],),
                }
            }
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
