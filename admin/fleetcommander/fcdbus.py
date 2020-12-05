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

from __future__ import absolute_import
import os
import sys
import json
import logging
import re
import time
from functools import wraps

import dbus
import dbus.service
import dbus.mainloop.glib

from gi.repository import GLib
from gi.repository import Gio

from . import sshcontroller
from . import libvirtcontroller
from .database import DBManager
from . import mergers
from .goa import GOAProvidersLoader
from . import fcfreeipa
from . import fcad

logger = logging.getLogger(os.path.basename(__file__))

SYSTEM_USER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,30}$")
IPADDRESS_AND_PORT_REGEX = re.compile(
    r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\:[0-9]{1,5})*$"
)
HOSTNAME_AND_PORT_REGEX = re.compile(
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])(\:[0-9]{1,5})?$"
)

DBUS_BUS_NAME = "org.freedesktop.FleetCommander"
DBUS_OBJECT_PATH = "/org/freedesktop/FleetCommander"
DBUS_INTERFACE_NAME = "org.freedesktop.FleetCommander"


def set_last_call_time(f):
    @wraps(f)
    def wrapped(obj, *args, **kwargs):
        obj._last_call_time = time.time()
        r = f(obj, *args, **kwargs)
        return r

    return wrapped


class FleetCommanderDbusService(dbus.service.Object):
    """
    Fleet commander d-bus service class
    """

    LIST_DOMAINS_RETRIES = 2

    REALMD_BUS = Gio.BusType.SYSTEM

    DEFAULT_HYPERVISOR_CONF = {
        "host": "",
        "username": "",
        "mode": "system",
        "viewer": "spice_html5",
    }

    def __init__(self, args):
        """
        Class initialization
        """
        super().__init__()

        # Set log level at initialization
        self.log_level = args["log_level"].lower()
        loglevel = getattr(logging, args["log_level"].upper())
        logging.basicConfig(level=loglevel, format=args["log_format"])

        self.home_dir = os.path.expanduser("~")

        if not os.path.exists(self.home_dir):
            logger.error(
                "%s directory does not exist.\n"
                "In order to have home directory automatically created you "
                "have the following options:\n"
                "- install freeipa-server using `--mkenablehomedir`;\n"
                "- call: `authconfig --enablemkhomedir --update`;\n"
                "- call: `authselect select sssd with-mkhomedir`;\n"
                "The user will have to log into the system in order to have "
                "their home directory created!",
                self.home_dir,
            )
            sys.exit(1)

        if "state_dir" in args:
            self.state_dir = args["state_dir"]
        else:
            # Set state dir to $HOME/.local/share/fleetcommander
            self.state_dir = os.path.join(self.home_dir, ".local/share/fleetcommander")

        if not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir)

        self.database_path = os.path.join(self.state_dir, "fleetcommander.db")

        self.args = args

        self.default_profile_priority = args["default_profile_priority"]

        # Configure realm connection and information
        domain, server = self.get_realm_details()
        self.realm_info = {"domain": domain, "server": server}
        if server == "active-directory":
            # Load Active Directory connector
            logger.debug("Activating Active Directory domain support for %s", domain)
            self.realm_connector = fcad.ADConnector(domain)
        else:
            # Load FreeIPA connector
            logger.debug("Activating IPA domain support for %s", domain)
            self.realm_connector = fcfreeipa.FreeIPAConnector()

        self.GOA_PROVIDERS_FILE = os.path.join(args["data_dir"], "fc-goa-providers.ini")

        # Initialize database
        self.db = DBManager(self.database_path)

        # Initialize change mergers
        self.changemergers = {
            "org.gnome.gsettings": mergers.GSettingsChangeMerger(),
            "org.libreoffice.registry": mergers.LibreOfficeChangeMerger(),
            "org.chromium.Policies": mergers.ChromiumChangeMerger(),
            "com.google.chrome.Policies": mergers.ChromiumChangeMerger(),
            "org.mozilla.firefox": mergers.FirefoxChangeMerger(),
            "org.mozilla.firefox.Bookmarks": mergers.FirefoxBookmarksChangeMerger(),
            "org.freedesktop.NetworkManager": mergers.NetworkManagerChangeMerger(),
        }

        # Initialize SSH controller
        self.ssh = sshcontroller.SSHController()
        self.known_hosts_file = os.path.join(self.home_dir, ".ssh/known_hosts")

        # Timeout values
        self.tmp_session_destroy_timeout = args["tmp_session_destroy_timeout"]
        self.auto_quit_timeout = args["auto_quit_timeout"]

        # operational attributes
        self._loop = None
        self._last_call_time = None
        self._last_heartbeat = None

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(DBUS_BUS_NAME, dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        self._loop = GLib.MainLoop()

        # Start session checking
        self.start_session_checking()

        # Set last call time to an initial value
        self._last_call_time = time.time()

        # Enter main loop
        self._loop.run()

    def get_realm_details(self):
        sssd_provider = Gio.DBusProxy.new_for_bus_sync(
            self.REALMD_BUS,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.realmd",
            "/org/freedesktop/realmd/Sssd",
            "org.freedesktop.realmd.Provider",
            None,
        )
        realms = sssd_provider.get_cached_property("Realms")

        if realms is None:
            logger.error(
                'It seems that "realmd" package is not installed.'
                ' "realmd" is used for retreiving information about the Realm.'
            )
            sys.exit(1)

        if len(realms) > 0:
            logger.debug("FC: realmd queried. Using realm object %s", realms[0])
            realm = Gio.DBusProxy.new_for_bus_sync(
                self.REALMD_BUS,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.realmd",
                realms[0],
                "org.freedesktop.realmd.Realm",
                None,
            )
            domain = str(realm.get_cached_property("Name")).replace("'", "")
            details = {str(k): str(v) for k, v in realm.get_cached_property("Details")}
            server = details.get("server-software", "ipa")
            logger.debug("FC: Realm details: %s (%s)", domain, server)
            return (domain, server)
        # Return unknown domain and use IPA as directory server
        return ("UNKNOWN", "ipa")

    def get_libvirt_controller(self):
        """
        Get a libvirtcontroller instance
        """
        hypervisor = self.db.config["hypervisor"]
        return libvirtcontroller.controller(
            viewer_type=hypervisor["viewer"],
            data_path=self.state_dir,
            username=hypervisor["username"],
            hostname=hypervisor["host"],
            mode=hypervisor["mode"],
        )

    def get_public_key(self):
        # Initialize LibVirtController to create keypair if needed
        ctrlr = libvirtcontroller.controller(
            viewer_type="spice_html5",
            data_path=self.state_dir,
            username=None,
            hostname=None,
            mode="system",
        )
        with open(ctrlr.public_key_file, "r") as fd:
            public_key = fd.read().strip()
            fd.close()
        return public_key

    def get_hypervisor_config(self):
        logger.debug("Getting hypervisor configuration")
        public_key = self.get_public_key()
        # Check hypervisor configuration
        data = {
            "pubkey": public_key,
        }
        if "hypervisor" not in self.db.config:
            data.update(self.DEFAULT_HYPERVISOR_CONF)
            data.update(
                {
                    "needcfg": True,
                }
            )
        else:
            data.update(self.db.config["hypervisor"])
        return data

    def get_domains(self, only_temporary=False):
        tries = 0
        while tries < self.LIST_DOMAINS_RETRIES:
            tries += 1
            try:
                domains = self.get_libvirt_controller().list_domains()
                if only_temporary:
                    domains = [d for d in domains if d["temporary"]]
                logger.debug("Domains retrieved: %s", domains)
                return domains
            except Exception as e:
                error = e
                logger.debug("Getting domain try %s: %s", tries, error)
        logger.error("Error retrieving domains %s", error)
        return None

    def stop_current_session(self):

        if "uuid" not in self.db.config:
            logger.error("There was no session started")
            return False, "There was no session started"

        domain_uuid = self.db.config["uuid"]

        del self.db.config["uuid"]
        del self.db.config["connection_details"]

        try:
            self.get_libvirt_controller().session_stop(domain_uuid)
        except Exception as e:
            logger.error("Error stopping session: %s", e)
            return False, "Error stopping session: %s" % e

        return True, None

    def start_session_checking(self):
        self._last_heartbeat = time.time()
        # Add callback for temporary sessions check
        GLib.timeout_add(1000, self.check_running_sessions)
        logger.debug("Started session checking")

    def parse_hypervisor_hostname(self, hostname):
        hostdata = hostname.split(":", maxsplit=1)
        if len(hostdata) == 2:
            host, port = hostdata
        else:
            host = hostdata[0]
            port = self.ssh.DEFAULT_SSH_PORT
        return host, port

    def check_running_sessions(self):
        """
        Checks currently running sessions and destroy temporary ones on timeout
        """
        time_passed = time.time() - self._last_heartbeat
        if time_passed > self.tmp_session_destroy_timeout:
            domains = self.get_domains(only_temporary=True)
            logger.debug("Currently active temporary sessions: %s", domains)
            if domains:
                logger.info("Destroying stalled sessions")
                # Stop current session
                current_uuid = self.db.config.get("uuid", False)
                if current_uuid:
                    logger.debug("Stopping current session: %s", current_uuid)
                    self.stop_current_session()
                for domain in domains:
                    ctrlr = self.get_libvirt_controller()
                    domain_uuid = domain["uuid"]
                    if current_uuid != domain_uuid:
                        try:
                            ctrlr.session_stop(domain_uuid)
                        except Exception as e:
                            logger.error(
                                "Error destroying session with UUID %s: %s",
                                domain_uuid,
                                e,
                            )
            if time.time() - self._last_call_time > self.auto_quit_timeout:
                # Quit service
                logger.debug("Closing Fleet Commander Admin service due to inactivity")
                self._loop.quit()
            else:
                logger.debug("Resetting timer for session check")
                self._last_heartbeat = time.time()
        return True

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetInitialValues(self):
        state = {
            "debuglevel": self.log_level,
            "defaults": {
                "profilepriority": self.default_profile_priority,
            },
            "realm": self.realm_info["domain"],
            "server_type": self.realm_info["server"],
        }
        return json.dumps(state)

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def DoDomainConnection(self):
        logger.debug("Connecting to domain server")
        try:
            self.realm_connector.connect()
            return json.dumps({"status": True})
        except Exception as e:
            logger.debug("Domain server connection failed: %s", e)
            return json.dumps(
                {"status": False, "error": "Error connecting to domain server"}
            )

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="b")
    def HeartBeat(self):
        # Update last heartbeat time
        self._last_heartbeat = time.time()
        return True

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="b")
    def CheckNeedsConfiguration(self):
        return "hypervisor" not in self.db.config

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetPublicKey(self):
        return self.get_public_key()

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def CheckHypervisorConfig(self, jsondata):
        logger.debug("Checking hypervisor configuration")
        errors = {}
        try:
            data = json.loads(jsondata)
        except json.JSONDecodeError:
            errors["json"] = "Invalid JSON data"
            return json.dumps({"status": False, "errors": errors})

        if not isinstance(data, dict):
            errors["data"] = "Invalid configuration data"
            return json.dumps({"status": False, "errors": errors})

        if set(data) != set(self.DEFAULT_HYPERVISOR_CONF):
            errors["schema"] = "Invalid configuration schema"
            return json.dumps({"status": False, "errors": errors})

        # Check username
        if not re.match(SYSTEM_USER_REGEX, data["username"]):
            errors["username"] = "Invalid username specified"
        # Check hostname
        if not re.match(HOSTNAME_AND_PORT_REGEX, data["host"]) and not re.match(
            IPADDRESS_AND_PORT_REGEX, data["host"]
        ):
            errors["host"] = "Invalid hostname specified"
        # Check libvirt mode
        if data["mode"] not in ("system", "session"):
            errors["mode"] = "Invalid session type"
        if data["viewer"] not in ("spice_html5", "spice_remote_viewer"):
            errors["viewer"] = "Unsupported libvirt viewer type"

        if errors:
            return json.dumps({"status": False, "errors": errors})

        return json.dumps({"status": True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetHypervisorConfig(self):
        return json.dumps(self.get_hypervisor_config())

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def SetHypervisorConfig(self, jsondata):
        data = json.loads(jsondata)
        # Save hypervisor configuration
        self.db.config["hypervisor"] = data
        return json.dumps({"status": True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def CheckKnownHost(self, hostname):
        host, port = self.parse_hypervisor_hostname(hostname)

        # Check if hypervisor is a known host
        known = self.ssh.check_known_host(self.known_hosts_file, host)

        if not known:
            # Obtain SSH fingerprint for host
            try:
                key_data = self.ssh.scan_host_keys(host, port)
                fprint = self.ssh.get_fingerprint_from_key_data(key_data)
                return json.dumps(
                    {
                        "status": False,
                        "fprint": fprint,
                        "keys": key_data,
                    }
                )
            except Exception as e:
                logger.error("Error getting hypervisor fingerprint: %s", e)
                return json.dumps(
                    {"status": False, "error": "Error connecting to SSH service."}
                )
        else:
            return json.dumps({"status": True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def AddKnownHost(self, hostname):
        host, port = self.parse_hypervisor_hostname(hostname)

        # Check if hypervisor is a known host
        known = self.ssh.check_known_host(self.known_hosts_file, host)

        if not known:
            try:
                self.ssh.add_to_known_hosts(self.known_hosts_file, host, port)
            except Exception as e:
                logger.error("Error adding host to known hosts: %s", e)
                return json.dumps(
                    {"status": False, "error": "Error adding host to known hosts"}
                )

        return json.dumps({"status": True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="sss", out_signature="s")
    def InstallPubkey(self, hostname, user, passwd):
        host, port = self.parse_hypervisor_hostname(hostname)
        pubkey = self.get_public_key()
        try:
            self.ssh.install_pubkey(pubkey, user, passwd, host, port)
            return json.dumps({"status": True})
        except Exception as e:
            logger.error("Error installing public key: %s", e)
            return json.dumps({"status": False, "error": "Error installing public key"})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetGlobalPolicy(self):
        logger.debug("Getting global policy")
        try:
            policy = self.realm_connector.get_global_policy()
            return json.dumps({"status": True, "policy": policy})
        except Exception as e:
            logger.error("Error getting global policy: %s", e)
            return json.dumps({"status": False, "error": "Error getting global policy"})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="q", out_signature="s")
    def SetGlobalPolicy(self, policy):

        logger.debug("Setting policy to %s", policy)

        try:
            self.realm_connector.set_global_policy(int(policy))
            return json.dumps({"status": True})
        except Exception as e:
            logger.error("Error setting global policy to %s: %s", policy, e)
            return json.dumps(
                {"status": False, "error": "Error setting given global policy"}
            )

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def SaveProfile(self, profiledata):
        logger.debug("Data received for saving profile: %s", profiledata)

        data = json.loads(profiledata)
        logger.debug("Data after JSON decoding: %s", data)

        profile = {
            "cn": data["cn"],
            "name": data["name"],
            "description": data["description"],
            "priority": int(data["priority"]),
            "settings": data["settings"],
            "groups": [
                _f for _f in [elem.strip() for elem in data["groups"].split(",")] if _f
            ],
            "users": [
                _f for _f in [elem.strip() for elem in data["users"].split(",")] if _f
            ],
            "hosts": [
                _f for _f in [elem.strip() for elem in data["hosts"].split(",")] if _f
            ],
            "hostgroups": [
                _f
                for _f in [elem.strip() for elem in data["hostgroups"].split(",")]
                if _f
            ],
        }

        logger.debug("Profile built to be saved: %s", profile)

        cn = profile["cn"]
        name = profile["name"]

        if "oldname" in data:
            logger.debug(
                "Profile is being renamed from %s to %s", data["oldname"], name
            )
            profile["oldname"] = data["oldname"]

        try:
            logger.debug("Saving profile into domain server")
            self.realm_connector.save_profile(profile)
            return json.dumps({"status": True})
        except fcfreeipa.RenameToExistingException as e:
            logger.error("Error saving profile %s (%s): %s", cn, name, e)
            return json.dumps({"status": False, "error": "%s" % e})
        except Exception as e:
            logger.error("Error saving profile %s: (%s) %s", cn, name, e)
            return json.dumps({"status": False, "error": "Can not save profile."})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetProfiles(self):
        try:
            profiles = self.realm_connector.get_profiles()
            logger.debug("Profiles data fetched: %s", profiles)
            return json.dumps({"status": True, "data": profiles})
        except Exception as e:
            logger.error("Error reading profiles from domain server: %s", e)
            return json.dumps(
                {"status": False, "error": "Error reading profiles index"}
            )

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def GetProfile(self, name):
        try:
            profile = self.realm_connector.get_profile(name)
            logger.debug("Profile data fetched for %s: %s", name, profile)
            return json.dumps({"status": True, "data": profile})
        except Exception as e:
            logger.error("Error reading profile %s from domain server: %s", name, e)
            return json.dumps(
                {
                    "status": False,
                    "error": "Error reading profile %s" % name,
                }
            )

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def DeleteProfile(self, name):
        logger.debug("Deleting profile %s", name)
        try:
            self.realm_connector.del_profile(name)
            return json.dumps({"status": True})
        except Exception as e:
            logger.error("Error removing profile %s: %s", name, e)
            return json.dumps({"status": False})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def ListDomains(self):
        domains = self.get_domains()
        if domains is not None:
            return json.dumps({"status": True, "domains": domains})
        return json.dumps({"status": False, "error": "Error retrieving domains"})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="s")
    def SessionStart(self, domain_uuid):

        logger.debug("Starting new session")
        if self.db.config.get("uuid", None) is not None:
            logger.error("Session already started")
            return json.dumps({"status": False, "error": "Session already started"})

        try:
            lvirtctrlr = self.get_libvirt_controller()
            session_params = lvirtctrlr.session_start(
                domain_uuid, debug_logger=self.args["debug_logger"]
            )
        except Exception as e:
            logger.error("Error starting session: %s", e)
            return json.dumps(
                {"status": False, "error": "Error starting session: {}".format(e)}
            )

        self.db.config["uuid"] = session_params.domain
        self.db.config["connection_details"] = session_params.details

        return json.dumps(
            {"status": True, "connection_details": session_params.details}
        )

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def SessionStop(self):
        status, msg = self.stop_current_session()
        if status:
            return json.dumps({"status": True})
        return json.dumps({"status": False, "error": msg})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="ss", out_signature="s")
    def SessionSave(self, uid, data):
        logger.debug("FC: Saving session")
        try:
            profile = self.realm_connector.get_profile(uid)
        except Exception as e:
            logger.debug("Could not parse profile %s: %s", uid, e)
            return json.dumps(
                {"status": False, "error": "Could not parse profile %s" % uid}
            )

        logger.debug("FC: Loaded profile")

        # Handle changesets
        try:
            changesets = json.loads(data)
        except Exception as e:
            logger.debug("Could not parse changeset: %s. Data: %s", e, data)
            return json.dumps(
                {"status": False, "error": "Could not parse changesets: %s" % data}
            )

        logger.debug("FC: Changesets loaded: %s", changesets)

        if not isinstance(changesets, dict):
            logger.debug("FC: Invalid changesets data")
            return json.dumps(
                {
                    "status": False,
                    "error": "Changesets should be a namespace/changes lists dict",
                }
            )

        # Save changes
        for ns, changeset in changesets.items():
            logger.debug("FC: Processing %s changeset: %s", ns, changeset)
            if not isinstance(changeset, list):
                logger.debug("FC: Invalid changeset: %s", ns)
                return json.dumps(
                    {"status": False, "error": "Changesets should be a change list"}
                )

            logger.debug("FC: Adding changes to profile")
            if ns not in profile["settings"]:
                logger.debug("FC: Adding new changeset into profile")
                profile["settings"][ns] = changeset
            else:
                if ns in self.changemergers:
                    logger.debug("FC: Merging changeset into profile")
                    profile["settings"][ns] = self.changemergers[ns].merge(
                        profile["settings"][ns], changeset
                    )
                else:
                    logger.debug("FC: No merger found for %s. Replacing changes", ns)
                    profile["settings"][ns] = changeset

        logger.debug("FC: Saving profile")
        self.realm_connector.save_profile(profile)
        logger.debug("FC: Saved profile")

        return json.dumps({"status": True})

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="s", out_signature="b")
    def IsSessionActive(self, uuid):
        if uuid == "":
            # Asking for current session
            if "uuid" in self.db.config:
                logger.debug(
                    "Checking for default session with uuid: %s", self.db.config["uuid"]
                )
                uuid = self.db.config["uuid"]
            else:
                logger.debug("Default session not started")
                return False

        domains = self.get_domains()
        for domain in domains:
            if domain["uuid"] == uuid:
                logger.debug("Session found: %s", domain)
                return domain["active"]
        logger.debug("Given session uuid not found in domains")
        return False

    @set_last_call_time
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="s")
    def GetGOAProviders(self):
        try:
            loader = GOAProvidersLoader(self.GOA_PROVIDERS_FILE)
            return json.dumps({"status": True, "providers": loader.get_providers()})
        except Exception as e:
            logger.error("Error getting GOA providers data: %s", e)
            return json.dumps(
                {"status": False, "error": "Error getting GOA providers data"}
            )

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature="", out_signature="")
    def Quit(self):
        self._loop.quit()


if __name__ == "__main__":

    # Python import
    from argparse import ArgumentParser

    # Fleet commander imports
    from .utils import parse_config

    parser = ArgumentParser(description="Fleet Commander Admin dbus service")
    parser.add_argument(
        "--configuration",
        action="store",
        metavar="CONFIGFILE",
        default=None,
        help="Provide a configuration file path for the service",
    )

    args = parser.parse_args()
    config = parse_config(args.configuration)

    svc = FleetCommanderDbusService(config)
    svc.run()
