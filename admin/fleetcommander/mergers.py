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

from __future__ import absolute_import
import logging

logger = logging.getLogger(__name__)


class BaseChangeMerger:
    """
    Base change merger class
    """

    KEY_NAME = "key"

    def get_key_from_change(self, change):
        """
        Return change key identifier
        """
        if self.KEY_NAME in change:
            return change[self.KEY_NAME]

        return None

    def merge(self, *args):
        """
        Merge changesets in the given order
        """
        index = {}
        for changeset in args:
            for change in changeset:
                key = self.get_key_from_change(change)
                index[key] = change
        return list(index.values())


class GSettingsChangeMerger(BaseChangeMerger):
    """
    GSettings change merger class
    """


class LibreOfficeChangeMerger(BaseChangeMerger):
    """
    LibreOffice change merger class
    """


class NetworkManagerChangeMerger(BaseChangeMerger):
    """
    Network manager change merger class
    """

    KEY_NAME = "uuid"


class ChromiumChangeMerger(BaseChangeMerger):
    """
    Chromium/Chrome change merger class
    """

    KEY_NAME = "key"

    def merge(self, *args):
        """
        Merge changesets in the given order
        """
        index = {}
        bookmarks = []
        for changeset in args:
            for change in changeset:
                key = self.get_key_from_change(change)
                if key == "ManagedBookmarks":
                    bookmarks = self.merge_bookmarks(bookmarks, change["value"])
                    change = {self.KEY_NAME: key, "value": bookmarks}
                index[key] = change
        return list(index.values())

    def merge_bookmarks(self, a, b):
        for elem_b in b:
            logger.debug("Processing %s", elem_b)
            if "children" in elem_b:
                merged = False
                for elem_a in a:
                    if elem_a["name"] == elem_b["name"] and "children" in elem_a:
                        logger.debug("Processing children of %s", elem_b["name"])
                        elem_a["children"] = self.merge_bookmarks(
                            elem_a["children"], elem_b["children"]
                        )
                        merged = True
                        break
                if not merged:
                    a.append(elem_b)
            else:
                if elem_b not in a:
                    a.append(elem_b)
        logger.debug("Returning %s", a)
        return a


class FirefoxChangeMerger(BaseChangeMerger):
    """
    Firefox settings change merger class
    """


class FirefoxBookmarksChangeMerger(BaseChangeMerger):
    """
    Firefox bookmarks change merger class
    """
