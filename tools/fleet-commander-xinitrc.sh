#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS

export DISPLAY=:35

# Check for the X display :35 socket every 200ms
for i in `seq 1 20`; do
  if test -S /tmp/.X11-unix/X35 ; then
    break
  fi

  sleep 0.2
done

#If the socket is still not there we quit
if test ! -S /tmp/.X11-unix/X35 ; then
  echo "ERROR: X session for fleet-commander was not present" >&2
  exit 1
fi

/etc/X11/xinit/xinitrc &
