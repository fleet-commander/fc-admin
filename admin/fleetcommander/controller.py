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
#

import sys
import os
import logging
import subprocess

from argparse import ArgumentParser

# Compat between Pyhon 2 and 3
try:
    from configparser import ConfigParser, ParsingError
except ImportError:
    from ConfigParser import ConfigParser, ParsingError

from flaskless import Flaskless, JSONResponse


class VncSessionManager(object):
    service = "fleet-commander-vnc-session.service"

    def start(self):
        if subprocess.call(["systemctl", "start", self.service]) != 0:
            return False
        return True

    def stop(self):
        subprocess.call(["systemctl", "stop", self.service])


class VncController(Flaskless):
    """
    Controller class for VNC sessions
    """
    def __init__(self, configuration=None, args=None):
        """
        Class initialization
        """

        routes = [
            (r'^vnc/port$',              ['GET'],    self.vnc_address),
            (r'^session/start$',         ['GET'],    self.new_session),
            (r'^session/stop$',          ['GET'],    self.stop_session),

        ]
        super(VncController, self).__init__(routes=routes)

        self.conf = self.parse_config(configuration, args)
        self.vnc = VncSessionManager()
        self.has_session = False
        self.STDPORT = 5935

    def parse_config(self, config_file=None, args=None):
        SECTION_NAME = 'controller'

        if args is None:
            args = {
                'host': 'localhost',
                'port': 8182,
                'logger_config': '/etc/xdg/fleet-commander-logger.conf'
            }

        if config_file is None:
            return args

        if not os.path.exists(config_file):
            logging.warning('Could not find configuration file %s' % config_file)
            sys.exit(1)

        config = ConfigParser()
        try:
            config.read(config_file)
        except ParsingError:
            logging.error('There was an error parsing %s' % config_file)
            sys.exit(1)
        except:
            logging.error('There was an unknown error parsing %s' % config_file)
            sys.exit(1)

        if not config.has_section(SECTION_NAME):
            logging.error('Configuration file %s has no "%s" section' % (config_file, SECTION_NAME))
            return args

        def config_to_dict(config):
            res = {}
            for g in config.sections():
                res[g] = {}
                for o in config.options(g):
                    res[g][o] = config.get(g, o)
            return res

        config = config_to_dict(config)

        args['host'] = config[SECTION_NAME].get('host', args['host'])
        args['port'] = config[SECTION_NAME].get('port', args['port'])
        args['logger_config'] = config[SECTION_NAME].get('logger_config', args['logger_config'])

        try:
            args['port'] = int(args['port'])
        except ValueError:
            logging.error("Error reading configuration at %s: 'port' option must be an integer value")
            sys.exit(1)

        return args

    def update_logger_config(self, host):
        SECTION_NAME = 'logger'
        config = ConfigParser()
        config_file = self.conf['logger_config']
        try:
            config.read(config_file)
        except ParsingError:
            logging.error('There was an error parsing %s' % config_file)
            return
        except:
            logging.error('There was an unknown error parsing %s' % config_file)
            return

        if not config.has_section(SECTION_NAME):
            config.add_section(SECTION_NAME)
        config.set(SECTION_NAME, 'admin_server_host', str(host))

        try:
            f = open(config_file, 'w')
            config.write(f)
            f.close()
        except:
            logging.error('There was an unknown error writing %s' % config_file)

    def vnc_address(self, request):
        return JSONResponse({'port': self.STDPORT})

    def new_session(self, request):
        print "START", self.has_session
        self.update_logger_config(request.host.split(":")[0])

        if self.has_session:
            return JSONResponse({"status": "already_started"}, 403)

        if not self.vnc.start():
            return JSONResponse({"status": "there was a problem starting the VNC session, check the journal"}, 403)

        self.has_session = True
        return JSONResponse({"status": "ok"}, 200)

    def stop_session(self, request):
        print "STOP", self.has_session
        if not self.has_session:
            return JSONResponse({"status": "already_stopped"}, 403)

        self.vnc.stop()

        self.has_session = False
        return JSONResponse({"status": "stopped"}, 200)


if __name__ == '__main__':
    parser = ArgumentParser(description='Fleet commander configuration session controller service')
    parser.add_argument(
        '--configuration', action='store', metavar='CONFIGFILE', default=None,
        help='Provide a configuration file path for the web service')

    args = parser.parse_args()
    app = VncController(args.configuration)
    app.run(host=app.conf['host'], port=app.conf['port'])
