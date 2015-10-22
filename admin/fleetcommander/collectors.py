#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

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

# Python imports
import json

class GoaCollector(object):

    """
    Gnome Online Accounts collector class
    """

    def __init__(self):
        self.json = {}

    def handle_change(self, request):
        self.json = dict(request.get_json())

    def get_settings(self):
        return self.json


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

    def handle_change(self, request):
        """
        Handle a change and store it
        """
        data = request.get_json()
        print data
        self.settings.update_setting(self.COLLECTOR_NAME, data['key'], request.content)

    def dump_changes(self):
        """
        Dump all changes in a sorted list
        """
        data = []
        changes = self.settings.get_for_collector(self.COLLECTOR_NAME)
        for key, change in sorted(changes.items()):
            data.append([key, json.loads(change)['value']])
        return data

    def remember_selected(self, selected_indices):
        """
        Mark given changes as selected
        """
        changes = self.settings.get_for_collector(self.COLLECTOR_NAME)
        selection = []
        sorted_keys = sorted(changes.keys())
        for index in selected_indices:
            if index < len(sorted_keys):
                key = sorted_keys[index]
                selection.append(key)

        if len(selection) > 0:
            self.settings.select_settings(self.COLLECTOR_NAME, selection)

    def get_settings(self):
        """
        Return a list of selected changes
        """
        changes = self.settings.get_for_collector(self.COLLECTOR_NAME, only_selected=True)
        keys = sorted(changes.keys())
        return [json.loads(changes[key]) for key in keys]


class GSettingsCollector(BaseCollector):
    """
    Gnome Online Accounts collector class
    """
    COLLECTOR_NAME = 'org.gnome.gsettings'

