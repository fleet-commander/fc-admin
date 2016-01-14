# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

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
import sys
import os
import logging
import tempfile

# Compat between Pyhon 2 and 3
try:
    from configparser import ConfigParser, ParsingError
except ImportError:
    from ConfigParser import ConfigParser, ParsingError


def parse_config(config_file, data_dir=None, state_dir=None, host=None, port=None):
    SECTION_NAME = 'admin'

    if state_dir is None:
        state_dir = os.path.join(tempfile.gettempdir(), 'fleet-commander-%s' % os.getuid())
        if not os.path.exists(state_dir):
            os.mkdir(state_dir)
        if not os.path.exists(os.path.join(state_dir, 'profiles')):
            os.mkdir(os.path.join(state_dir, 'profiles'))

    if data_dir is None:
        data_dir = state_dir

    args = {
        'host': host or 'localhost',
        'port': port or 8181,
        'data_dir': data_dir,
        'state_dir': state_dir,
        'profiles_dir': os.path.join(state_dir, 'profiles'),
        'database_path': os.path.join(state_dir, 'database.db'),
    }

    if not config_file:
        return args

    config = ConfigParser()
    try:
        config.read(config_file)
    except IOError:
        logging.warning('Could not find configuration file %s' % config_file)
    except ParsingError:
        logging.error('There was an error parsing %s' % config_file)
        sys.exit(1)
    except:
        logging.error('There was an unknown error parsing %s' % config_file)
        raise

    if not config.has_section(SECTION_NAME):
        return args

    def config_to_dict(config):
        res = {}
        for g in config.sections():
            res[g] = {}
            for o in config.options(g):
                res[g][o] = config.get(g, o)
        return res

    config = config_to_dict(config)
    if host is None:
        args['host'] = config[SECTION_NAME].get('host', args['host'])
    if port is None:
        args['port'] = config[SECTION_NAME].get('port', args['port'])
    if data_dir is None:
        args['data_dir'] = config[SECTION_NAME].get('data_dir', args['data_dir'])
    if state_dir is None:
        args['state_dir'] = config[SECTION_NAME].get('state_dir', args['state_dir'])

    args['profiles_dir'] = config[SECTION_NAME].get('profiles_dir', args['profiles_dir'])
    args['database_path'] = config[SECTION_NAME].get('database_path', args['database_path'])

    try:
        args['port'] = int(args['port'])
    except ValueError:
        logging.error("Error reading configuration file %s: 'port' option must be an integer value" % config_file)
        sys.exit(1)

    return args
