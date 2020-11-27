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

if [ "x$TOPSRCDIR" = "x" ] ; then
  TOPSRCDIR=`pwd`/../
fi

# We assume dbus-launch never fails
eval `dbus-launch`
export DBUS_SESSION_BUS_ADDRESS

dconf write /org/libreoffice/registry/somepath/somekey 123

export FC_TESTING=true
export GSETTINGS_SCHEMA_DIR=`mktemp -d`

cp $TOPSRCDIR/tests/data/test.gschema.xml $GSETTINGS_SCHEMA_DIR
if [ $? -ne 0 ] ; then
  echo "Failed to copy schema file to tempdir" >&2
  exit 1
fi

glib-compile-schemas $GSETTINGS_SCHEMA_DIR
if [ $? -ne 0 ] ; then
  echo "Failed to copy schema file to tempdir" >&2
  exit 1
fi

RET=1

# We assume dbus-launch never fails
kill $DBUS_SESSION_BUS_PID
eval `dbus-launch`
export DBUS_SESSION_BUS_ADDRESS

$PYTHON $TOPSRCDIR/tests/_mock_dbus.py > /dev/null 2> /dev/null &
DBUS_MOCK_PID=$!

$PYTHON $TOPSRCDIR/tests/_wait_for_name.py org.freedesktop.ScreenSaver
if [ $? -ne 0 ] ; then
  echo "Failed to acquire bus name org.freedesktop.ScreenSaver"
  exit 1
fi

ps -p $DBUS_MOCK_PID > /dev/null 2> /dev/null
if [ $? -ne 0 ] ; then
  echo "Failed to launch _mock_dbus.py" >&2
  exit 1
fi

$PYTHON $TOPSRCDIR/tests/_logger_test_suite.py
RET=$?

rm -rf $GSETTINGS_SCHEMA_DIR
kill $DBUS_MOCK_PID
kill $DBUS_SESSION_BUS_PID
exit $RET
