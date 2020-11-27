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

# We assume dbus-launch never fails

kill $DBUS_SESSION_BUS_PID > /dev/null 2> /dev/null

eval `dbus-launch`
export DBUS_SESSION_BUS_ADDRESS


$PYTHON $TOPSRCDIR/tests/_mock_realmd_dbus.py &
DBUS_MOCK_PID=$!

$PYTHON $TOPSRCDIR/tests/_wait_for_name.py org.freedesktop.realmd
if [ $? -ne 0 ] ; then
  echo "Failed to acquire bus name org.freedesktop.realmd"
  exit 1
fi

ps -p $DBUS_MOCK_PID > /dev/null 2> /dev/null
if [ $? -ne 0 ] ; then
  echo "Failed to launch _mock_realmd_dbus.py"
  exit 1
fi

# Execute fleet commander dbus service tests
$PYTHON $TOPSRCDIR/tests/_fcdbus_tests.py
RET=$?

kill $DBUS_SESSION_BUS_PID

rm $TOPSRCDIR/_build/sub/admin/fleetcommander/constants.pyc > /dev/null 2>&1

exit $RET
