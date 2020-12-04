# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2015 Red Hat, Inc.
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

from __future__ import absolute_import
from six.moves.configparser import RawConfigParser, ParsingError
import logging

logger = logging.getLogger(__name__)


class GOAProvidersLoader:
    """
    GOA providers reader
    """

    def __init__(self, providers_file):
        """
        Class initialization
        """
        self.path = providers_file
        self._providers = {}
        self._configparser = RawConfigParser()
        try:
            self._configparser.read(providers_file)
        except IOError as e:
            logger.error("Could not find GOA providers file %s", providers_file)
            raise e
        except ParsingError as e:
            logger.error("There was an error parsing %s", providers_file)
            raise e
        except Exception as e:
            logger.error("There was an unknown error parsing %s", providers_file)
            raise e
        self.read_data()

    def read_data(self):
        for section in self._configparser.sections():
            if section.startswith("Provider "):
                provider = section.split()[1]
                self._providers[provider] = {
                    "name": self.generate_readable_name(provider),
                    "services": {},
                }
                for option in self._configparser.options(section):
                    if option == "providername":
                        name = self._configparser.get(section, option)
                        self._providers[provider]["name"] = name
                    elif option.endswith("enabled"):
                        service = option[:-7].title() + "Enabled"
                        name = self.generate_readable_name(service[:-7])
                        enabled = self._configparser.getboolean(section, option)
                        # Generate readable name
                        self._providers[provider]["services"][service] = {
                            "name": name,
                            "enabled": enabled,
                        }

    def generate_readable_name(self, identifier):
        """
        Generates readable names for providers and services
        """
        stripped = identifier.strip()
        if stripped:
            return stripped.title().replace("_", " ")
        return "Enabled"

    def get_providers(self):
        return self._providers
