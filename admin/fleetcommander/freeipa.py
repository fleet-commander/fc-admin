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

    def check_profile_exists(self, uid):
        try:
            result = api.Command.deskprofile_show(unicode(uid), all=False)
            return True
        except errors.NotFound:
            return False

    def create_profile(self, profile):
        uid = unicode(profile['uid'])
        try:
            api.Command.deskprofile_add(
                uid,
                description=unicode(profile['description']),
                ipadeskdata=json.dumps(profile['settings'])
            )
            self.create_profile_rules(profile)
        except Exception, e:
            logging.error(
                'FC - FreeIPAConnector: Error creating profile: %s' % e)
            self.del_profile(uid)
            raise e

    def create_profile_rules(self, profile):
        uid = unicode(profile['uid'])
        # Save rule for profile
        api.Command.deskprofilerule_add(
            uid,
            ipadeskprofiletarget=uid,
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

    def update_profile(self, profile):
        uid = unicode(profile['uid'])
        try:
            # Update profile
            api.Command.deskprofile_mod(
                uid,
                description=unicode(profile['description']),
                ipadeskdata=json.dumps(profile['settings'])
            )
        except errors.EmptyModlist:
            pass
        except Exception, e:
            logging.error(
                'FC - FreeIPAConnector: Error updating profile %s: %s' % (uid, e))
            raise e

        self.update_profile_rules(profile)

    def update_profile_rules(self, profile):
        uid = unicode(profile['uid'])
        # update rule for profile
        try:
            api.Command.deskprofilerule_mod(
                uid,
                ipadeskprofiletarget=uid,
                ipadeskprofilepriority=profile['priority'])
        except errors.EmptyModlist:
            pass
        except Exception, e:
            logging.error(
                'FC - FreeIPAConnector: Error updating rule for profile %s: %s - %s' % (uid, e, e.__class__))
            raise e
        # Get current users, groups, hosts and hostgroups for this rule
        rule = self.get_profile_rule(uid)
        applies = self.get_profile_applies_from_rule(rule)
        # Get users and groups to add
        udif = set(profile['users']) - set(applies['users'])
        gdif = set(profile['groups']) - set(applies['groups'])
        # Add the users and groups to rule
        api.Command.deskprofilerule_add_user(
            uid,
            user=map(unicode, udif),
            group=map(unicode, gdif)
        )
        # Get users and groups to remove
        udif = set(applies['users']) - set(profile['users'])
        gdif = set(applies['groups']) - set(profile['groups'])
        # Remove users and groups from rule
        api.Command.deskprofilerule_remove_user(
            uid,
            user=map(unicode, udif),
            group=map(unicode, gdif)
        )

        # Get hosts and hostgroups to add
        hdif = set(profile['hosts']) - set(applies['hosts'])
        hgdif = set(profile['hostgroups']) - set(applies['hostgroups'])
        # Add the hosts and hostgroups to rule
        api.Command.deskprofilerule_add_host(
            uid,
            host=map(unicode, hdif),
            hostgroup=map(unicode, hgdif)
        )
        # Get hosts and hostgroups to remove
        hdif = set(applies['hosts']) - set(profile['hosts'])
        hgdif = set(applies['hostgroups']) - set(profile['hostgroups'])
        # Remove hosts and hostgroups from rule
        api.Command.deskprofilerule_remove_host(
            uid,
            host=map(unicode, hdif),
            hostgroup=map(unicode, hgdif)
        )

    def save_profile(self, profile):
        # Check if profile already exists
        if self.check_profile_exists(profile['uid']):
            # Modify it
            return self.update_profile(profile)
        else:
            # Save new
            return self.create_profile(profile)

    def del_profile(self, uid):
        uid = unicode(uid)
        try:
            api.Command.deskprofile_del(uid)
        except Exception, e:
            logging.debug(
                'FC - FreeIPAConnector: Error removing profile %s. %s - %s' % (uid, e, e.__class__))

        try:
            api.Command.deskprofilerule_del(uid)
        except Exception, e:
            logging.debug(
                'FC - FreeIPAConnector: Error removing rule for profile %s. %s - %s' % (uid, e, e.__class__))

    def get_profiles(self):
        try:
            results = api.Command.deskprofile_find('', all=True)
        except Exception, e:
            logging.error(
                'FC - FreeIPAConnector: Error getting profiles: %s - %s' % (e, e.__class__))
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
            logging.error(
                'Error getting profile %s: %s. %s' % (uid, e, e.__class__))
            raise e
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
            logging.error(
                'Error getting rule for profile %s: %s. %s' % (uid, e, e.__class__))
            raise e
        return result['result']

    def get_profile_applies_from_rule(self, rule):
        applies = {
            'users': [],
            'groups': [],
            'hosts': [],
            'hostgroups': [],
        }
        if 'memberuser_user' in rule:
            applies['users'] = rule['memberuser_user']
        if 'memberuser_group' in rule:
            applies['groups'] = rule['memberuser_group']
        if 'memberhost_host' in rule:
            # Remove domain part from hostnames
            applies['hosts'] = [
                x.split('.')[0] for x in rule['memberhost_host']]
        if 'memberhost_hostgroup' in rule:
            applies['hostgroups'] = rule['memberhost_hostgroup']
        return applies
