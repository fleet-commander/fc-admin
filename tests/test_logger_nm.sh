#!/bin/bash

# We assume dbus-launch never fails

kill $DBUS_SESSION_BUS_PID > /dev/null 2> /dev/null

eval `dbus-launch`
export DBUS_SESSION_BUS_ADDRESS


$PYTHON $TOPSRCDIR/tests/_mock_nm_dbus.py &
DBUS_MOCK_PID=$!

$PYTHON $TOPSRCDIR/tests/_wait_for_name.py org.freedesktop.NetworkManager
if [ $? -ne 0 ] ; then
  echo "Failed to acquire bus name org.freedesktop.NetworkManager"
  exit 1
fi

ps -p $DBUS_MOCK_PID > /dev/null 2>&1
if [ $? -ne 0 ] ; then
  echo "Failed to launch _mock_nm_dbus.py"
  exit 1
fi

# Execute fleet commander NM logger tests
$PYTHON $TOPSRCDIR/tests/_logger_nm.py
RET=$?

kill $DBUS_SESSION_BUS_PID

rm $TOPSRCDIR/_build/sub/admin/fleetcommander/constants.pyc > /dev/null 2>&1

exit $RET
