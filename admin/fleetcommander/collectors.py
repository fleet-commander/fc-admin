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
        self.json = dict(request.json)

    def get_settings(self):
        return self.json


class GSettingsCollector(object):

    def __init__(self):
        self.changes = {}
        self.selection = []

    def remember_selected(self, selected_indices):
        self.selection = []
        sorted_keys = sorted(self.changes.keys())
        for index in selected_indices:
            if index < len(sorted_keys):
                key = sorted_keys[index]
                change = self.changes[key]
                self.selection.append(change)

    def handle_change(self, request):
        data = request.get_json()
        self.changes[data['key']] = data

    def dump_changes(self):
        data = []
        for key, change in sorted(self.changes.items()):
            data.append([key, change['value']])
        return data

    def get_settings(self):
        return self.selection
