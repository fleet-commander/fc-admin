#!/bin/bash

# Copyright (c) 2015 Red Hat, Inc.
#
# GNOME Maps is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# GNOME Maps is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Maps; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutierrez <ogutierrez@redhat.com>

if [ "x$TOPSRCDIR" = "x" ] ; then
  TOPSRCDIR=`pwd`/../
fi

export TOPSRCDIR

# We assume dbus-launch never fails
eval `dbus-launch`
export DBUS_SESSION_BUS_ADDRESS

# Create test directory
FC_TEST_DIRECTORY=$(mktemp -d)
export FC_TEST_DIRECTORY

# Execute fleet commander dbus service
$TOPSRCDIR/tests/_05_fcdbus.py > /dev/null 2> /dev/null &
DBUS_SERVICE_PID=$!

# Execute fleet commander dbus service tests
$TOPSRCDIR/tests/_05_fcdbus_tests.py
RET=$?

#kill $DBUS_SERVICE_PID
#kill $DBUS_SESSION_BUS_PID

#rm -rf $FC_TEST_DIRECTORY
#exit $RET
