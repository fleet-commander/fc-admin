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
import logging

# Compat between Pyhon 2 and 3
try:
    from configparser import ConfigParser, ParsingError
except ImportError:
    from six.moves.configparser import ConfigParser, ParsingError

from . import constants

logger = logging.getLogger(__name__)


def parse_config(config_file=None):
    if config_file is None:
        config_file = constants.DEFAULT_CONFIG_FILE

    config = ConfigParser()
    try:
        config.read(config_file)
    except IOError:
        logger.warning("Could not find configuration file %s", config_file)
    except ParsingError:
        logger.error("There was an error parsing %s", config_file)
        raise
    except Exception as e:
        logger.error("There was an unknown error parsing %s: %s", config_file, e)
        raise e

    section = config["admin"]
    args = {
        "default_profile_priority": section.getint(
            "default_profile_priority", constants.DEFAULT_PROFILE_PRIORITY
        ),
        "log_level": section.get("log_level", constants.DEFAULT_LOG_LEVEL),
        "log_format": section.get("log_format", constants.DEFAULT_LOG_FORMAT),
        "data_dir": section.get("data_dir", constants.DEFAULT_DATA_DIR),
        "tmp_session_destroy_timeout": section.getint(
            "tmp_session_destroy_timeout",
            constants.DEFAULT_TMP_SESSION_DESTROY_TIMEOUT,
        ),
        "auto_quit_timeout": section.getint(
            "auto_quit_timeout", constants.DEFAULT_AUTO_QUIT_TIMEOUT
        ),
        "debug_logger": section.getboolean(
            "debug_logger", constants.DEFAULT_DEBUG_LOGGER
        ),
    }

    return args
