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

import json
import logging
import uuid

from ipalib import api
from ipalib import errors


class FreeIPAConnector(object):

    def __init__(self):
        self.connect()

    def connect(self):
        """
        Connect to FreeIPA server
        """
        if not api.isdone('bootstrap'):
            api.bootstrap(context='cli', log=None)
            api.finalize()

        if not api.Backend.rpcclient.isconnected():
            api.Backend.rpcclient.connect()
        api.Command.ping()

    def check_user_exists(self, username):
        try:
            result = api.Command.user_show(unicode(username))
            return True
        except errors.NotFound:
            return False

    def check_group_exists(self, groupname):
        try:
            result = api.Command.group_show(unicode(groupname))
            return True
        except errors.NotFound:
            return False

    def check_host_exists(self, hostname):
        try:
            result = api.Command.host_show(unicode(hostname))
            return True
        except errors.NotFound:
            return False

    def check_hostgroup_exists(self, groupname):
        try:
            result = api.Command.hostgroup_show(unicode(groupname))
            return True
        except errors.NotFound:
            return False

    def save_profile(self, profile):
        uid = unicode(profile['uid'])
        renuid = unicode(uuid.uuid1().int)
        try:
            # Rename profile
            api.Command.deskprofile_mod(uid, rename=renuid)
            # Rename profile rule
            api.Command.deskprofilerule_mod(
                uid, rename=renuid, ipadeskprofiletarget=renuid)
            # TODO: Find a way to get clean state
        except:
            renuid = None
        try:
            api.Command.deskprofile_add(
                uid,
                description=unicode(profile['description']),
                ipadeskdata=json.dumps(profile['settings'])
            )
            # Save rule for profile
            api.Command.deskprofilerule_add(
                uid, ipadeskprofiletarget=uid,
                ipadeskprofilepriority=profile['priority'])
            # Save rules for users
            api.Command.deskprofilerule_add_user(
                uid,
                user=map(unicode, profile['users']),
                group=map(unicode, profile['groups'])
            )
            # Save rules for hosts
            api.Command.deskprofilerule_add_host(
                uid,
                host=map(unicode, profile['hosts']),
                hostgroup=map(unicode, profile['hostgroups'])
            )
            if renuid is not None:
                self.del_profile(renuid)
            return uid
        except Exception, e:
            print("Error saving profile: %s" % e)
            self.del_profile(uid)
            if renuid is not None:
                try:
                    api.Command.deskprofile_mod(renuid, rename=uid)
                    api.Command.deskprofilerule_mod(
                        renuid, rename=uid, ipadeskprofiletarget=uid)
                except:
                    pass

    def del_profile(self, uid):
        uid = unicode(uid)
        try:
            api.Command.deskprofile_del(uid)
        except errors.NotFound:
            print("Profile %s does not exist" % uid)
        except Exception, e:
            print("Error removing %s. %s" % (uid, e.__class__))

        try:
            api.Command.deskprofilerule_del(uid)
        except Exception, e:
            print("Error removing rule for %s. %s" % (uid, e.__class__))

    def get_profiles(self):
        try:
            results = api.Command.deskprofile_find('', all=True)
        except Exception, e:
            print(
                "Error getting profiles %s" % e.__class__)
        else:
            resultlist = []
            for res in results['result']:
                desc = ''
                if 'description' in res:
                    desc = res['description'][0]
                resultlist.append(
                    (res['cn'][0], desc)
                )
            return resultlist

    def get_profile(self, uid):
        uid = unicode(uid)
        try:
            result = api.Command.deskprofile_show(uid, all=True)
        except Exception, e:
            print("Error getting profile %s. %s" % (uid, e.__class__))
        else:
            rule = self.get_profile_rule(uid)
            data = result['result']
            profile = {
                'uid': data['cn'][0],
                'description': data['description'][0],
                'priority': int(rule['ipadeskprofilepriority'][0]),
                'settings': json.loads(data['ipadeskdata'][0]),
            }
            applies = self.get_profile_applies_from_rule(rule)
            profile.update(applies)
            return profile

    def get_profile_rule(self, uid):
        uid = unicode(uid)
        try:
            result = api.Command.deskprofilerule_show(uid, all=True)
        except Exception, e:
            print("Error getting rule for profile %s. %s" % (uid, e.__class__))
        else:
            return result['result']

    def get_profile_applies_from_rule(self, rule):
        applies = {
            'users': rule['memberuser_user'],
            'groups': rule['memberuser_group'],
            'hosts': rule['memberhost_host'],
            'hostgroups': rule['memberhost_hostgroup'],
        }
        return applies
