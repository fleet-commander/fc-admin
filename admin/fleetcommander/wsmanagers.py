#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2014 Red Hat, Inc.
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
import subprocess


class WebSockifyManager(object):

    """
    WebSockify WebSocket manager class
    """

    _COMMAND_TEMPLATE = "websockify %s:%d %s:%d"

    def __init__(self, **kwargs):
        """
        Construction arguments:
            listen_host: host to listen for WS connections
            listen_port: port to listen for WS connections
            target_host: native socket host connection
            target_port: native socket port connection
        """
        self.listen_host = kwargs.get('listen_host', 'localhost')
        self.listen_port = kwargs.get('listen_port', 8989)
        self.target_host = kwargs.get('target_host', 'localhost')
        self.target_port = kwargs.get('target_port', 5900)
        self.websockify = None
        self.DNULL = open('/dev/null', 'w')

    def start(self):
        if self.websockify:
            return

        command = self._COMMAND_TEMPLATE % (
            self.listen_host, self.listen_port,
            self.target_host, self.target_port)

        self.websockify = subprocess.Popen(
            command, shell=True,
            stdin=self.DNULL, stdout=self.DNULL, stderr=self.DNULL)

    def stop(self):
        if self.websockify:
            self.websockify.kill()
            self.websockify = None


class VncWebsocketManager(WebSockifyManager):
    pass
