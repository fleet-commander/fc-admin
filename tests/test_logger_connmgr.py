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
from __future__ import division
from __future__ import print_function

import json
import logging
import math
import os
import re
import unittest

from unittest.mock import mock_open, patch

# GObject Introspection imports
from gi.repository import Gio

from fleet_commander_logger import (
    FC_LOGGER_PROTO_CHUNK_SIZE,
    FC_LOGGER_PROTO_HEADER,
    FC_LOGGER_PROTO_SUFFIX,
)
import fleet_commander_logger as FleetCommander

logger = logging.getLogger(os.path.basename(__file__))


def read_file(filename):
    with open(filename) as fd:
        return fd.read()


def parse_fc_message(msg):
    """Parser for completely received message of FleetCommander Logger.

    Return list of JSON objects.
    """
    m = re.match(rf"^{FC_LOGGER_PROTO_HEADER}(.*){FC_LOGGER_PROTO_SUFFIX}$", msg)
    return m.group(1).split(FC_LOGGER_PROTO_SUFFIX)


class TestConnMgr(unittest.TestCase):
    """Test SpicePortManager."""

    def test_01_proto_version(self):
        """Test SpicePortManager sends logger protocol version on instantiation."""
        TMPFILE = Gio.file_new_tmp("fc_logger_spiceport_XXXXXX")
        path = TMPFILE[0].get_path()
        FleetCommander.SpicePortManager(path)

        # Check PROTO header has been written to spiceport file
        raw_data = read_file(path)
        self.assertEqual(raw_data, FC_LOGGER_PROTO_HEADER)

    def test_02_submit_change(self):
        # Get temporary file
        TMPFILE = Gio.file_new_tmp("fc_logger_spiceport_XXXXXX")
        path = TMPFILE[0].get_path()
        mgr = FleetCommander.SpicePortManager(path)
        PAYLOAD = '["PAYLOAD"]'
        expected_data = ['{"ns": "org.gnome.gsettings", "data": "[\\"PAYLOAD\\"]"}']
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
        raw_data = read_file(path)
        actual = parse_fc_message(raw_data)
        self.assertListEqual(actual, expected_data)
        # check that the change is correct dumped JSON object
        # dump it again for string comparison
        self.assertEqual(
            json.dumps(json.loads(actual[0])), json.dumps(json.loads(expected_data[0]))
        )

    def test_03_manager_queue(self):
        # Get temporary file
        TMPFILE = Gio.file_new_tmp("fc_logger_spiceport_XXXXXX")
        path = TMPFILE[0].get_path()

        mgr = FleetCommander.SpicePortManager(path)
        PAYLOADS = ["1", "2", "3", "4", "5"]
        expected_data = []

        for pl in PAYLOADS:
            mgr.submit_change("org.gnome.gsettings", pl)
            expected_data.append(json.dumps({"ns": "org.gnome.gsettings", "data": pl}))

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
        raw_data = read_file(path)
        actual = parse_fc_message(raw_data)
        self.assertListEqual(actual, expected_data)

    def test_04_big_message(self):
        """Test logger sends a data in chunks."""
        path = "/logger_notify_channel"
        payload = "A" * 32768

        with patch("builtins.open", mock_open(), create=True) as m:
            mgr = FleetCommander.SpicePortManager(path)

        m.assert_called_once_with(path, "wb", 0)
        fd = m()
        fd.write.assert_called_once_with(FC_LOGGER_PROTO_HEADER.encode())
        fd.write.reset_mock()

        mgr.submit_change("org.gnome.gsettings", payload)

        # Check change is in queue
        self.assertEqual(len(mgr.queue), 1)
        self.assertEqual(mgr.queue[0]["ns"], "org.gnome.gsettings")
        self.assertEqual(mgr.queue[0]["data"], payload)

        # Clean queue and quit
        mgr.give_up()
        self.assertEqual(len(mgr.queue), 0)
        self.assertEqual(mgr.timeout, 0)

        # Check data has been written to the mocked file
        expected_data = (
            json.dumps({"ns": "org.gnome.gsettings", "data": payload})
            + FC_LOGGER_PROTO_SUFFIX
        ).encode()

        expected_chunks_count = math.ceil(
            len(expected_data) / FC_LOGGER_PROTO_CHUNK_SIZE
        )
        self.assertEqual(fd.write.call_count, expected_chunks_count)

        actual_data = b""
        for call_args in fd.write.call_args_list:
            write_args, _ = call_args
            self.assertEqual(len(write_args), 1)
            actual_data += write_args[0]

        self.assertEqual(actual_data, expected_data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
