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


class BaseChangeMerger(object):
    """
    Base change merger class
    """
    KEY_NAME = 'key'

    def get_key_from_change(self, change):
        """
        Return change key identifier
        """
        if self.KEY_NAME in change:
            return change[self.KEY_NAME]

    def merge(self, *args):
        """
        Merge changesets in the given order
        """
        index = {}
        for changeset in args:
            for change in changeset:
                key = self.get_key_from_change(change)
                index[key] = change
        return index.values()


class GSettingsChangeMerger(BaseChangeMerger):
    """
    GSettings change merger class
    """
    pass


class LibreOfficeChangeMerger(BaseChangeMerger):
    """
    LibreOffice change merger class
    """
    pass


class NetworkManagerChangeMerger(BaseChangeMerger):
    """
    Network manager change merger class
    """
    KEY_NAME = 'uuid'
