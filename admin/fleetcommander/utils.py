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
from __future__ import absolute_import
import os
import sys
import logging
import socket
import six

# Compat between Pyhon 2 and 3
try:
    from configparser import ConfigParser, ParsingError
except ImportError:
    from six.moves.configparser import ConfigParser, ParsingError

from . import constants


def get_data_from_file(path):
    with open(path, 'r') as fd:
        data = fd.read()
        fd.close()
        return data


def test_and_create_file(path, content):
    if os.path.isfile(path):
        return
    with open(path, 'w+') as fd:
        fd.write(content)


def write_and_close(path, data):
    f = open(path, 'w+')
    f.write(data)
    f.close()


def config_to_dict(config):
    """
    Convert a configuration object into a dictionary
    """
    res = {}
    for g in config.sections():
        res[g] = {}
        for o in config.options(g):
            res[g][o] = config.get(g, o)
    return res


def parse_config(config_file=None):
    if config_file is None:
        config_file = constants.DEFAULT_CONFIG_FILE

    config = ConfigParser()
    try:
        config.read(config_file)
    except IOError:
        logging.warning('Could not find configuration file %s', config_file)
    except ParsingError:
        logging.error('There was an error parsing %s', config_file)
        sys.exit(1)
    except Exception as e:
        logging.error(
            'There was an unknown error parsing %s: %s', config_file, e
        )
        sys.exit(1)

    if config.has_section('admin'):
        config = config_to_dict(config)
        section = config['admin']
    else:
        section = {}

    args = {
        'default_profile_priority': section.get(
            'default_profile_priority', constants.DEFAULT_PROFILE_PRIORITY),
        'log_level': section.get(
            'log_level', constants.DEFAULT_LOG_LEVEL),
        'log_format': section.get(
            'log_format', constants.DEFAULT_LOG_FORMAT),
        'webservice_host': section.get(
            'webservice_host', constants.DEFAULT_WEBSERVICE_HOST),
        'webservice_port': section.get(
            'webservice_port', constants.DEFAULT_WEBSERVICE_PORT),
        'data_dir': section.get(
            'data_dir', constants.DEFAULT_DATA_DIR),
        'client_data_url': section.get(
            'client_data_url', constants.DEFAULT_CLIENT_DATA_URL),
        'tmp_session_destroy_timeout': section.get(
            'tmp_session_destroy_timeout',
            constants.DEFAULT_TMP_SESSION_DESTROY_TIMEOUT),
        'auto_quit_timeout': section.get(
            'auto_quit_timeout',
            constants.DEFAULT_AUTO_QUIT_TIMEOUT),
    }

    if not args['client_data_url'][-1] == args['client_data_url'][0] == '/':
        logging.error('Client data URL must start and end with /')
        sys.exit(1)

    return args


def get_ip_address(hostname):
    """
    Returns first IP address for given hostname
    """
    data = socket.gethostbyname(hostname)
    return six.text_type(data)
