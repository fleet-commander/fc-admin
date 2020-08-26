#!/usr/bin/env python-wrapper.sh
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

# Python imports
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import json
import logging
import unittest

# GObject Introspection imports
from gi.repository import Gio

PYTHONPATH = os.path.join(os.environ["TOPSRCDIR"], "logger")
sys.path.append(PYTHONPATH)

import fleet_commander_logger as FleetCommander

# Set logging level to debug
log = logging.getLogger()
level = logging.getLevelName("DEBUG")
log.setLevel(level)


def read_file(filename):
    with open(filename, "r") as fd:
        data = fd.read()
        fd.close()
    return data


class TestConnMgr(unittest.TestCase):
    def setUp(self):
        pass

    def test_01_submit_change(self):
        # Get temporary file
        TMPFILE = Gio.file_new_tmp("fc_logger_spiceport_XXXXXX")
        path = TMPFILE[0].get_path()
        mgr = FleetCommander.SpicePortManager(path)
        PAYLOAD = '["PAYLOAD"]'
        expected_data = '{"ns": "org.gnome.gsettings", "data": "[\\"PAYLOAD\\"]"}'
        mgr.submit_change("org.gnome.gsettings", PAYLOAD)

        # Check change is in queue
        self.assertEqual(len(mgr.queue), 1)
        self.assertEqual(mgr.queue[0]["ns"], "org.gnome.gsettings")
        self.assertEqual(mgr.queue[0]["data"], PAYLOAD)

        # Clean queue and quit
        mgr.give_up()
        self.assertEqual(len(mgr.queue), 0)
        self.assertEqual(mgr.timeout, 0)

        # Check data has been written to spiceport file
        data = read_file(path)
        self.assertEqual(
            json.dumps(json.loads(expected_data)), json.dumps(json.loads(data))
        )

    def test_02_manager_queue(self):
        # Get temporary file
        TMPFILE = Gio.file_new_tmp("fc_logger_spiceport_XXXXXX")
        path = TMPFILE[0].get_path()

        mgr = FleetCommander.SpicePortManager(path)
        PAYLOADS = ["1", "2", "3", "4", "5"]
        expected_data = ""

        for pl in PAYLOADS:
            mgr.submit_change("org.gnome.gsettings", pl)
            expected_data += json.dumps({"ns": "org.gnome.gsettings", "data": pl})

        self.assertEqual(len(PAYLOADS), len(mgr.queue))

        index = 0
        for elem in mgr.queue:
            self.assertEqual(elem["ns"], "org.gnome.gsettings")
            self.assertEqual(elem["data"], PAYLOADS[index])
            index += 1

        # Clean queue and quit
        mgr.give_up()
        self.assertEqual(len(mgr.queue), 0)
        self.assertEqual(mgr.timeout, 0)

        # Check data has been written to spiceport file
        data = read_file(path)
        self.assertEqual(expected_data, data)


if __name__ == "__main__":
    unittest.main()
