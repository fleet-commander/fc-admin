from __future__ import absolute_import

import dbus
import time
import sys
from six.moves import range

if __name__ == '__main__':
    session = dbus.Bus()
    for i in range(20):
        for name in session.list_names():
            if name == "org.freedesktop.ScreenSaver":
                sys.exit(0)
        time.sleep(0.05)
sys.exit(1)
