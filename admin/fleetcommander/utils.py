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
import logging
import copy
import socket

# Compat between Pyhon 2 and 3
try:
    from configparser import ConfigParser, ParsingError
except ImportError:
    from ConfigParser import ConfigParser, ParsingError

import constants


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
        logging.warning('Could not find configuration file %s' % config_file)
    except ParsingError:
        logging.error('There was an error parsing %s' % config_file)
        sys.exit(1)
    except Exception, e:
        logging.error(
            'There was an unknown error parsing %s: %s' %
            config_file, e)
        sys.exit(1)

    if config.has_section(constants.CONFIG_SECTION_NAME):
        config = config_to_dict(config)
        section = config[constants.CONFIG_SECTION_NAME]
    else:
        section = {}

    args = {
        'webservice_host': section.get(
            'webservice_host', constants.DEFAULT_WEBSERVICE_HOST),
        'webservice_port': section.get(
            'webservice_port', constants.DEFAULT_WEBSERVICE_PORT),
        'data_dir': section.get(
            'data_dir', constants.DEFAULT_DATA_DIR),
        'state_dir': section.get(
            'state_dir', constants.DEFAULT_STATE_DIR),
        'profiles_dir': section.get(
            'profiles_dir', constants.DEFAULT_PROFILES_DIR),
        'database_path': section.get(
            'database_path', constants.DEFAULT_DATABASE_PATH),
        'client_data_url': section.get(
            'client_data_url', constants.DEFAULT_CLIENT_DATA_URL),
        'tmp_session_destroy_timeout': section.get(
            'tmp_session_destroy_timeout',
            constants.DEFAULT_TMP_SESSION_DESTROY_TIMEOUT),
    }

    if not args['client_data_url'][-1] == args['client_data_url'][0] == '/':
        logging.error('Client data URL must start and end with /')
        sys.exit(1)

    return args


def merge_settings(a, b):
    result = copy.deepcopy(a)
    for domain in b:
        if domain not in result:
            result[domain] = b[domain]
            continue

        index = {}
        for change in a[domain]:
            index[change["key"]] = change

        for change in b[domain]:
            key = change["key"]
            index[key] = change

        result[domain] = [index[key] for key in index]

    return result


def get_ip_address(hostname):
    """
    Returns first IP address for given hostname
    """
    data = socket.gethostbyname(hostname)
    return unicode(data)
