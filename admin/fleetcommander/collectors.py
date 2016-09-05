# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2014 Red Hat, Inc.
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
#

import json
import logging


class DummyCollector:
    """
    Dummy collector class
    """

    def __init__(self, *args, **kwargs):
        pass

    def handle_change(self, change):
        """
        Handle a change and store it
        """
        pass

    def dump_changes(self):
        """
        Dump all changes in a sorted list
        """
        return []

    def remember_selected(self, selected_keys):
        """
        Mark given changes as selected
        """
        pass

    def get_settings(self):
        """
        Return a list of selected changes
        """
        return []

    def merge_settings(self, profile_settings):
        """
        Merge given settings pair
        """
        return []


class BaseCollector(object):
    """
    Base collector class
    """

    COLLECTOR_NAME = 'basecollector'

    def __init__(self, db):
        """
        Class initialization
        """
        self.db = db
        self.settings = self.db.sessionsettings

    def get_key_from_change(self, change):
        """
        Return change key identifier
        """
        if 'key' in change:
            return change['key']

    def get_value_from_change(self, change):
        """
        Return change human readable value
        """
        if 'value' in change:
            return change['value']
        return 'Undefined'

    def handle_change(self, change):
        """
        Handle a change and store it
        """
        key = self.get_key_from_change(change)
        if key is not None:
            self.settings.update_setting(
                self.COLLECTOR_NAME,
                key,
                json.dumps(change))
        else:
            logging.error('%s: Given change is invalid: %s' % (
                self.COLLECTOR_NAME,
                json.dumps(change)
            ))

    def dump_changes(self):
        """
        Dump all changes in a sorted list
        """
        data = []
        changes = self.settings.get_for_collector(self.COLLECTOR_NAME)
        for key, change in sorted(changes.items()):
            value = self.get_value_from_change(json.loads(change))
            data.append([key, value])
        return data

    def remember_selected(self, selected_keys):
        """
        Mark given changes as selected
        """
        changes = self.settings.get_for_collector(self.COLLECTOR_NAME)
        selection = []
        for key in selected_keys:
            if key in changes:
                selection.append(key)

        if len(selection) > 0:
            self.settings.select_settings(self.COLLECTOR_NAME, selection)

    def get_settings(self):
        """
        Return a list of selected changes
        """
        changes = self.settings.get_for_collector(
            self.COLLECTOR_NAME, only_selected=True)
        keys = sorted(changes.keys())
        return [json.loads(changes[key]) for key in keys]

    def merge_settings(self, profile_settings):
        """
        Return a list of selected changes
        """
        current = self.get_settings()
        index = {}
        for changeset in [profile_settings, current]:
            for change in changeset:
                index[change["key"]] = change
        return index.values()


class GSettingsCollector(BaseCollector):
    """
    GSettings collector class
    """
    COLLECTOR_NAME = 'org.gnome.gsettings'


class LibreOfficeCollector(BaseCollector):
    """
    LibreOffice collector class
    """
    COLLECTOR_NAME = 'org.libreoffice.registry'


class NetworkManagerCollector(BaseCollector):
    """
    Network manager collector class
    """
    COLLECTOR_NAME = 'org.freedesktop.NetworkManager'

    def get_key_from_change(self, change):
        """
        Return change key identifier for NM connection
        """
        try:
            return change[u'uuid']
        except:
            return

    def get_value_from_change(self, change):
        """
        Return change human readable value for NM connection
        """
        try:
            return '%s - %s' % (change[u'type'], change[u'id']),
        except:
            return 'Undefined'
