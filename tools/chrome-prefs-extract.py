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
# Author: Oliver Gutiérrez <ogutierrez@redhat.com>

# This script is intended to generate a json data file with a mapping between
# preferences and policies so we can use them into logger.
# Source data is got from:
#    https://cs.chromium.org/chromium/src/chrome/test/data/policy/policy_test_cases.json

from __future__ import absolute_import
import sys
import json

inputfile = open(sys.argv[1], "r")
outputfile = open(sys.argv[2], "wb")

data = json.loads(inputfile.read())

outdata = {}
for key, value in data.items():
    if "pref_mappings" in value:
        if value["pref_mappings"] and "pref" in value["pref_mappings"][0]:
            outdata[value["pref_mappings"][0]["pref"]] = key

outputfile.write(json.dumps(outdata))
