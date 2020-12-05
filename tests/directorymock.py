# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2018, 2019 Red Hat, Inc.
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
# Authors: Oliver Gutiérrez <ogutierrez@redhat.com>
#          Alberto Ruiz <aruiz@redhat.com>


import os
import logging
import json


class DirectoryData:
    def __init__(self, datadir=None):
        logging.debug("Directory mock data initialized. Path: %s", datadir)
        self.datadir = datadir
        # Data storage
        self.global_policy = 1
        self.profiles = {}

    def get_json(self):
        data = {
            "policy": self.global_policy,
            "profiles": self.profiles,
        }
        logging.debug("Directory mock data to export: %s", data)
        jsondata = json.dumps(data)
        logging.debug("Directory mock JSON data to export: %s", jsondata)
        return jsondata

    def save_to_datadir(self, filename="directorymock-data.json"):
        if self.datadir is not None:
            path = os.path.join(self.datadir, filename)
            logging.debug("Directory mock exporting data to %s", path)
            with open(path, "w") as fd:
                fd.write(self.get_json())

            logging.debug("Directory mock data saved to %s", path)
        else:
            logging.debug("Directory mock not exporting data (No datadir)")

    # Decorator for exporting data to file
    @classmethod
    def export_data(cls, fun):
        def wrapper(self, *args, **kwargs):
            result = fun(self, *args, **kwargs)
            # Save data storaged in data member
            self.data.save_to_datadir()
            return result

        return wrapper


class DirectoryConnector:
    """
    Directory connector module mocking class
    """

    data = None

    def __init__(self, domain=None):
        pass

    def connect(self, sanity_check=True):
        """
        Connect to AD server
        """
        logging.debug("Directory Mock: Connection")

    def get_global_policy(self):
        return self.data.global_policy

    @DirectoryData.export_data
    def set_global_policy(self, policy):
        self.data.global_policy = policy

    @DirectoryData.export_data
    def save_profile(self, profile):
        # Check if profile already exists
        cn = profile.get("cn", None)
        if cn is not None:
            # Modifying existing profile
            logging.debug("Directory Mock: Trying to modify profile with cn %s", cn)
            if cn in self.data.profiles:
                logging.debug("Directory Mock: Modifying existing profile %s", cn)
            else:
                logging.debug("Directory Mock: Profile %s does not exist. Saving.", cn)
            self.data.profiles[cn] = profile
        else:
            # Saving new profile
            cn = profile["name"]
            logging.debug(
                "Directory Mock: Saving new profile. Using name as new id: %s", cn
            )
            self.data.profiles[cn] = profile
        return cn

    @DirectoryData.export_data
    def del_profile(self, cn):
        logging.debug("Directory Mock: Deleting profile %s", cn)
        if cn in self.data.profiles:
            del self.data.profiles[cn]

    def get_profiles(self):
        logging.debug("Directory Mock: Getting profile list")
        profiles = []
        for cn, profile in self.data.profiles.items():
            profiles.append((cn, profile["name"], profile["description"]))
        return profiles

    def get_profile(self, cn):
        logging.debug("Directory Mock: Getting profile %s", cn)
        return self.data.profiles.get(cn, dict())
