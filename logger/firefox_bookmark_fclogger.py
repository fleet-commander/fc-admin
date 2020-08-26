# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2019 Red Hat, Inc.
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

import sys
import json
import struct
import time
import logging
import dbus
from functools import wraps


DBUS_BUS_NAME = 'org.freedesktop.FleetCommanderLogger'
DBUS_OBJECT_PATH = '/org/freedesktop/FleetCommanderLogger'
DBUS_INTERFACE_NAME = 'org.freedesktop.FleetCommanderLogger'


def connected_to_dbus_service(f):
    @wraps(f)
    def wrapped(obj, *args, **kwargs):
        if obj.iface is None:
            obj.connect()
        if obj.iface is None:
            logging.error('Not connected to FC Logger dbus service')
            return None
        r = f(obj, *args, **kwargs)
        return r

    return wrapped


class FleetCommanderLoggerDbusClient:
    """
    Fleet commander logger dbus client
    """

    DEFAULT_BUS = dbus.SessionBus
    CONNECTION_TIMEOUT = 1

    def __init__(self, bus=None):
        """
        Class initialization
        """
        self.obj = None
        self.iface = None

        if bus is None:
            bus = self.DEFAULT_BUS()
        self.bus = bus

    def connect(self):
        """
        Connect to dbus service
        """
        logging.debug('Connecting to FC Logger dbus service')
        t = time.time()
        while time.time() - t < self.CONNECTION_TIMEOUT:
            try:
                self.obj = self.bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
                self.iface = dbus.Interface(
                    self.obj, dbus_interface=DBUS_INTERFACE_NAME)
                return
            except Exception:
                logging.debug('Can\'t connect to FC Logger dbus service')

    @connected_to_dbus_service
    def firefox_bookmark_update(self, bookmark_id, data):
        return self.iface.FirefoxBookmarkUpdate(bookmark_id, data)

    @connected_to_dbus_service
    def firefox_bookmark_remove(self, bookmark_id):
        return self.iface.FirefoxBookmarkRemove(bookmark_id)


class FirefoxExtensionMessagingHelper:
    """
    Firefox messaging helper class
    """

    def __init__(self):
        # Set shortcuts for standard input and output buffers
        try:
            # Python 3
            self.stdin_buffer = sys.stdin.buffer
            self.stdout_buffer = sys.stdout.buffer
        except AttributeError:
            # Python 2
            self.stdin_buffer = sys.stdin
            self.stdout_buffer = sys.stdout

    def get_message(self):
        """
        Read a message from stdin and decode it
        """
        raw_length = self.stdin_buffer.read(4)
        if len(raw_length) == 0:
            sys.exit(0)
        message_length = struct.unpack('@I', raw_length)[0]
        message = self.stdin_buffer.read(message_length).decode('utf-8')
        return json.loads(message)

    def encode_message(self, content):
        """
        Encode a message for transmission
        """
        encoded_content = json.dumps(content).encode('utf-8')
        encoded_length = struct.pack('@I', len(encoded_content))
        return {'length': encoded_length, 'content': encoded_content}

    def send_message(self, message):
        """
        Send an encoded message to stdout
        """
        encoded_message = self.encode_message(message)
        self.stdout_buffer.write(encoded_message['length'])
        self.stdout_buffer.write(encoded_message['content'])
        self.stdout_buffer.flush()


extension = FirefoxExtensionMessagingHelper()
fclogger = FleetCommanderLoggerDbusClient()


while True:
    message = extension.get_message()
    bookmark_id = message['id']
    if message['action'] in ['add', 'change', 'move']:
        extension.send_message(
            'Received bookmark {} for bookmark id {}'.format(message['action'], bookmark_id))
        logging.debug(
            'Sending bookmark %s command to FC Logger dbus service',
            message['action']
        )
        fclogger.firefox_bookmark_update(bookmark_id, json.dumps(message))
    elif message['action'] == 'remove':
        extension.send_message('Received bookmark remove command for bookmark id {}'.format(bookmark_id))
        fclogger.firefox_bookmark_remove(bookmark_id)
    else:
        logging.debug('Unknown action received from extension')
