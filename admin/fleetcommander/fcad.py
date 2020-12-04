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
import json
import logging
import uuid
import getpass
import tempfile
import optparse  # pylint: disable=deprecated-module

from functools import wraps

import dns.resolver

import ldap
import ldap.sasl
import ldap.modlist

import samba
import samba.getopt as options
from samba.credentials import Credentials, MUST_USE_KERBEROS
from samba.ndr import ndr_unpack, ndr_pack
from samba.dcerpc import security
from samba.ntacls import dsacl2fsacl
from samba.samba3 import param as s3param

logger = logging.getLogger(__name__)

try:
    from samba.samba3 import libsmb
except ImportError:
    from samba.samba3 import libsmb_samba_internal as libsmb


GPO_SMB_PATH = "\\\\%s\\SysVol\\%s\\Policies\\%s"
SMB_DIRECTORY_PATH = "smb://%s/SysVol/%s/Policies/%s"

GPO_APPLY_GROUP_POLICY_CAR = "edacfd8f-ffb3-11d1-b41d-00a0c968f939"

FC_PROFILE_PREFIX = "_FC_%s"

FC_GLOBAL_POLICY_NS = "org.freedesktop.FleetCommander"
FC_GLOBAL_POLICY_PROFILE_NAME = "GLOBAL_POLICY__DO_NOT_MODIFY"
FC_GLOBAL_POLICY_DEFAULT = 1
FC_GLOBAL_POLICY_PROFILE = {
    "name": FC_GLOBAL_POLICY_PROFILE_NAME,
    "description": "Fleet Commander global settings profile. DO NOT MODIFY",
    "priority": 50,
    "settings": {
        FC_GLOBAL_POLICY_NS: {
            "global_policy": FC_GLOBAL_POLICY_DEFAULT,
        },
    },
    "users": [],
    "groups": [],
    "hosts": [],
    "hostgroups": [],
}

DEFAULT_GPO_SECURITY_DESCRIPTOR = "".join(
    [
        "O:%s",
        "G:%s",
        "D:PAI",
        "%s",
        "(OA;CI;CR;edacfd8f-ffb3-11d1-b41d-00a0c968f939;;AU)",
        "(A;;RPWPCCDCLCLORCWOWDSDDTSW;;;S-1-5-21-1754900228-1619607556-2970117160-512)",
        "%s",
        "(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;S-1-5-21-1754900228-1619607556-2970117160-512)",
        "(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;S-1-5-21-1754900228-1619607556-2970117160-519)",
        "(A;CI;RPLCLORC;;;ED)",
        "(A;CI;RPLCLORC;;;AU)",
        "(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;SY)",
        "(A;CIIO;RPWPCCDCLCLORCWOWDSDDTSW;;;CO)",
        "S:AI",
        "(OU;CIIDSA;WPWD;;f30e3bc2-9ff0-11d1-b603-0000f80367c1;WD)",
        "(OU;CIIOIDSA;WP;f30e3bbe-9ff0-11d1-b603-0000f80367c1;bf967aa5-0de6-11d0-a285-00aa003049e2;WD)",
        "(OU;CIIOIDSA;WP;f30e3bbf-9ff0-11d1-b603-0000f80367c1;bf967aa5-0de6-11d0-a285-00aa003049e2;WD)",
    ]
)
GPO_DACL_ACE = "(OA;CI;CR;edacfd8f-ffb3-11d1-b41d-00a0c968f939;;%s)"
GPO_DACL_ACCESS_ACE = "(A;CI;RPLCRC;;;%s)"


DEFAULT_PROFILE_JSON_DATA = json.dumps({"priority": 50, "settings": {}})


def connection_required(f):
    @wraps(f)
    def wrapped(obj, *args, **kwargs):
        obj.connect()
        return f(obj, *args, **kwargs)

    return wrapped


class ADConnector:
    """
    Active Directory connector class for Fleet Commander
    """

    CACHED_DOMAIN_DN = None
    CACHED_SERVER_NAME = None

    def __init__(self, domain):
        logger.debug("Initializing domain %s AD connector", domain)
        self.domain = domain
        dn = self._get_domain_dn().encode()
        self.GPO_BASE_ATTRIBUTES = {
            "objectClass": [b"top", b"container", b"groupPolicyContainer"],
            "flags": b"0",
            "versionNumber": b"1",
            "objectCategory": b"CN=Group-Policy-Container,CN=Schema,CN=Configuration,%s"
            % dn,
        }
        self.connection = None

    def _get_domain_dn(self):
        if self.CACHED_DOMAIN_DN is None:
            self.CACHED_DOMAIN_DN = "DC=%s" % ",DC=".join(self.domain.split("."))
        return self.CACHED_DOMAIN_DN

    def _get_server_name(self):
        logger.debug("Getting LDAP service machine name")
        # Resolve LDAP service machine
        if self.CACHED_SERVER_NAME is None:
            result = dns.resolver.query(
                "_ldap._tcp.dc._msdcs.%s" % self.domain.lower(), "SRV"
            )
            self.CACHED_SERVER_NAME = str(result[0].target)[:-1]
        logger.debug("LDAP server: %s", self.CACHED_SERVER_NAME)
        return self.CACHED_SERVER_NAME

    def _generate_gpo_uuid(self):
        return "{%s}" % str(uuid.uuid4()).upper()

    def _get_smb_connection(self, service="SysVol"):
        # Create options like if we were using command line
        parser = optparse.OptionParser()
        sambaopts = options.SambaOptions(parser)
        # Samba options
        parm = sambaopts.get_loadparm()
        s3_lp = s3param.get_context()
        s3_lp.load(parm.configfile)
        # Build credentials from credential options
        creds = Credentials()
        # Credentials need username and realm to be not empty strings to work
        creds.set_username("NOTEMPTY")
        creds.set_realm("NOTEMPTY")
        # Connect to SMB using kerberos
        creds.set_kerberos_state(MUST_USE_KERBEROS)
        # Create connection
        conn = libsmb.Conn(
            self._get_server_name(), service, lp=parm, creds=creds, sign=False
        )
        return conn

    def _load_smb_data(self, gpo_uuid):
        conn = self._get_smb_connection()
        furi = "%s\\Policies\\%s\\fleet-commander.json" % (self.domain, gpo_uuid)
        data = json.loads(conn.loadfile(furi))
        return data

    def _prepare_gpo_data(self, profile):
        # Create GPO data locally in a temporary directory
        logger.debug("Preparing GPO data locally")
        gpodir = tempfile.mkdtemp()
        # Machine and user directories
        os.mkdir(os.path.join(gpodir, "Machine"))
        os.mkdir(os.path.join(gpodir, "User"))
        # GPT file
        gpt_contents = "[General]\r\nVersion=0\r\n"
        with open(os.path.join(gpodir, "GPT.INI"), "w") as fd:
            fd.write(gpt_contents)
            fd.close()
        with open(os.path.join(gpodir, "fleet-commander.json"), "w") as fd:
            fd.write(
                json.dumps(
                    {
                        "priority": profile["priority"],
                        "settings": profile["settings"],
                    }
                )
            )
            fd.close()
        return gpodir

    def _copy_directory_local_to_remote(
        self, conn, localdir, remotedir, ignore_existing=False
    ):
        """
        Copied from Samba netcmd GPO code
        """
        logger.debug("Copying GPO from %s to %s", localdir, remotedir)
        if not conn.chkpath(remotedir):
            conn.mkdir(remotedir)
        l_dirs = [localdir]
        r_dirs = [remotedir]
        while l_dirs:
            l_dir = l_dirs.pop()
            r_dir = r_dirs.pop()

            dirlist = os.listdir(l_dir)
            dirlist.sort()
            for e in dirlist:
                l_name = os.path.join(l_dir, e)
                r_name = r_dir + "\\" + e

                if os.path.isdir(l_name):
                    l_dirs.append(l_name)
                    r_dirs.append(r_name)
                    try:
                        conn.mkdir(r_name)
                    except samba.NTSTATUSError:
                        if not ignore_existing:
                            raise
                else:
                    with open(l_name, "rb") as fd:
                        data = fd.read()
                        fd.close()
                    conn.savefile(r_name, data)

    def _save_smb_data(self, gpo_uuid, profile, sddl=None):
        logger.debug("Saving profile settings in CIFs share")

        # Prepare GPO data locally
        gpodir = self._prepare_gpo_data(profile)

        conn = self._get_smb_connection()

        # Create remote directory
        duri = "%s\\Policies\\%s" % (self.domain, gpo_uuid)
        logger.debug("Creating directory %s", duri)
        if not conn.chkpath(duri):
            conn.mkdir(duri)
        # Check if we need to set ACLs
        if sddl is not None:
            self._set_smb_permissions(conn, duri, sddl)
        # Copy local data to remote directory
        self._copy_directory_local_to_remote(conn, gpodir, duri, True)

    def _set_smb_permissions(self, conn, duri, sddl):
        logger.debug("Setting CIFs permissions for %s", duri)
        # Generate secuity descriptor from SDDL
        dom_sid = self.get_domain_sid()
        fsacl = dsacl2fsacl(sddl, dom_sid)
        fssd = security.descriptor.from_sddl(fsacl, dom_sid)
        # Set ACL
        sio = (
            security.SECINFO_OWNER
            | security.SECINFO_GROUP
            | security.SECINFO_DACL
            | security.SECINFO_PROTECTED_DACL
        )
        conn.set_acl(duri, fssd, sio)

    def _remove_smb_data(self, gpo_uuid):
        logger.debug("Removing CIFs data for GPO %s", gpo_uuid)
        # Connect to SMB using kerberos
        conn = self._get_smb_connection()
        # Remove directory and its contents
        duri = duri = "%s\\Policies\\%s" % (self.domain, gpo_uuid)
        conn.deltree(duri)

    def _get_ldap_profile_data(self, s_filter, controls=None):
        logger.debug("Getting data from AD LDAP. filter: %s", s_filter)
        base_dn = "CN=Policies,CN=System,%s" % self._get_domain_dn()
        attrs = ["cn", "displayName", "description", "nTSecurityDescriptor"]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        if len(resultlist) > 0:
            return resultlist[0][1]
        return None

    def _data_to_profile(self, data):
        cn = data["cn"][0].decode()
        logger.debug("Converting LDAP data for %s to profile", cn)
        name = data.get("displayName", (cn,))[0].decode()
        desc = data.get("description", (b"",))[0].decode()
        # Load settings and priority from samba file
        smb_data = self._load_smb_data(cn)
        profile = {
            "cn": cn,
            "name": name[len(FC_PROFILE_PREFIX) - 2 :],
            "description": desc,
            "priority": smb_data["priority"],
            "settings": smb_data["settings"],
        }
        # Load security descriptor, parse it and get applies data
        sdh = SecurityDescriptorHelper(data["nTSecurityDescriptor"][0], self)
        logger.debug("Loaded security descriptor data: %s", sdh.to_sddl())
        applies = sdh.get_fc_applies()
        profile.update(applies)
        return profile

    def _security_descriptor_from_profile(self, profile):
        # Security descriptor
        current_user = getpass.getuser().split("@")[0]
        current_user_sid = self.get_user(current_user)["sid"]
        gpo_aces = ""
        gpo_access_aces = ""

        for user in profile["users"]:
            obj = self.get_user(user)
            if obj is not None:
                gpo_aces += GPO_DACL_ACE % obj["sid"]
                gpo_access_aces += GPO_DACL_ACCESS_ACE % obj["sid"]
            else:
                logger.warning("User %s does not exist. Ignoring.", user)

        for group in profile["groups"]:
            obj = self.get_group(group)
            if obj is not None:
                gpo_aces += GPO_DACL_ACE % obj["sid"]
                gpo_access_aces += GPO_DACL_ACCESS_ACE % obj["sid"]
            else:
                logger.warning("Group %s does not exist. Ignoring.", group)

        for host in profile["hosts"]:
            obj = self.get_host(host)
            if obj is not None:
                gpo_aces += GPO_DACL_ACE % obj["sid"]
                gpo_access_aces += GPO_DACL_ACCESS_ACE % obj["sid"]
            else:
                logger.warning("Host %s does not exist. Ignoring.", host)

        shd = SecurityDescriptorHelper(
            DEFAULT_GPO_SECURITY_DESCRIPTOR
            % (current_user_sid, current_user_sid, gpo_aces, gpo_access_aces),
            self,
        )
        return shd.to_sd()

    def connect(self, sanity_check=True):
        """
        Connect to AD server
        """
        # TODO: Check LDAP connection to avoid binding every time
        logger.debug("Connecting to AD LDAP server")
        server_name = self._get_server_name()
        # Connect to LDAP using Kerberos
        logger.debug("Initializing LDAP connection to %s", server_name)
        self.connection = ldap.initialize("ldap://%s" % server_name)
        self.connection.set_option(ldap.OPT_REFERRALS, 0)
        sasl_auth = ldap.sasl.sasl({}, "GSSAPI")
        self.connection.protocol_version = 3
        logger.debug("Binding LDAP connection")
        self.connection.sasl_interactive_bind_s("", sasl_auth)
        logger.debug("LDAP connection succesful")

    @connection_required
    def get_global_policy(self):
        logger.debug("Getting global policy from AD")
        ldap_filter = "(displayName=%s)" % (
            FC_PROFILE_PREFIX % FC_GLOBAL_POLICY_PROFILE_NAME
        )
        data = self._get_ldap_profile_data(ldap_filter)
        if data:
            profile = self._data_to_profile(data)
            return profile["settings"][FC_GLOBAL_POLICY_NS]["global_policy"]
        return FC_GLOBAL_POLICY_DEFAULT

    @connection_required
    def set_global_policy(self, policy):
        ldap_filter = "(displayName=%s)" % (
            FC_PROFILE_PREFIX % FC_GLOBAL_POLICY_PROFILE_NAME
        )
        data = self._get_ldap_profile_data(ldap_filter)
        if data:
            profile = self._data_to_profile(data)
        else:
            profile = FC_GLOBAL_POLICY_PROFILE.copy()
        profile["settings"][FC_GLOBAL_POLICY_NS]["global_policy"] = policy
        self.save_profile(profile)

    @connection_required
    def save_profile(self, profile):
        # Check if profile exists
        cn = profile.get("cn", None)
        # Check if profile exists
        old_profile = None
        if cn is not None:
            ldap_filter = "(CN=%s)" % cn
            old_profile_data = self._get_ldap_profile_data(ldap_filter)
            if old_profile_data:
                old_profile = self._data_to_profile(old_profile_data)
        if old_profile is not None:
            logger.debug("Profile with cn %s already exists. Modifying", cn)
            logger.debug("Old profile: %s", old_profile)
            logger.debug("New profile: %s", profile)
            # Modify existing profile
            sd = self._security_descriptor_from_profile(profile)
            gpo_uuid = profile["cn"]
            ldif = [
                (
                    ldap.MOD_REPLACE,
                    "displayName",
                    (FC_PROFILE_PREFIX % profile["name"]).encode(),
                ),
                (ldap.MOD_REPLACE, "nTSecurityDescriptor", ndr_pack(sd)),
            ]
            if profile["description"]:
                ldif.append(
                    (ldap.MOD_REPLACE, "description", profile["description"].encode())
                )
            else:
                ldif.append((ldap.MOD_REPLACE, "description", None))

            logger.debug("LDIF data to be sent to LDAP: %s", ldif)
            dn = "CN=%s,CN=Policies,CN=System,%s" % (gpo_uuid, self._get_domain_dn())
            logger.debug("Modifying profile under %s", dn)
            self.connection.modify_s(dn, ldif)
            self._save_smb_data(gpo_uuid, profile, sd.as_sddl())
        else:
            logger.debug("Saving new profile")
            # Create new profile
            gpo_uuid = self._generate_gpo_uuid()
            logger.debug("New profile UUID = %s", gpo_uuid)
            attrs = self.GPO_BASE_ATTRIBUTES.copy()
            attrs["cn"] = gpo_uuid.encode()
            attrs["displayName"] = (FC_PROFILE_PREFIX % profile["name"]).encode()
            attrs["description"] = profile["description"].encode()
            attrs["gPCFileSysPath"] = (
                GPO_SMB_PATH % (self._get_server_name(), self.domain, gpo_uuid)
            ).encode()
            logger.debug("Preparing security descriptor")
            sd = self._security_descriptor_from_profile(profile)
            attrs["nTSecurityDescriptor"] = ndr_pack(sd)
            logger.debug("Profile data to be sent to LDAP: %s", attrs)
            ldif = ldap.modlist.addModlist(attrs)
            logger.debug("LDIF data to be sent to LDAP: %s", ldif)
            dn = "CN=%s,CN=Policies,CN=System,%s" % (gpo_uuid, self._get_domain_dn())
            logger.debug("Adding profile under %s", dn)
            self.connection.add_s(dn, ldif)
            # Save SMB data
            self._save_smb_data(gpo_uuid, profile, sd.as_sddl())
        return gpo_uuid

    @connection_required
    def del_profile(self, name):
        dn = "CN=%s,CN=Policies,CN=System,%s" % (name, self._get_domain_dn())
        try:
            self.connection.delete_s(dn)
        except ldap.LDAPError as e:
            logger.error("Error deleting %s: %s", name, e)
        # Remove samba files
        self._remove_smb_data(name)

    @connection_required
    def get_profiles(self):
        profiles = []
        base_dn = "CN=Policies,CN=System,%s" % self._get_domain_dn()
        s_filter = "(objectclass=groupPolicyContainer)"
        attrs = [
            "cn",
            "displayName",
            "description",
        ]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        for res in resultlist:
            resdata = res[1]
            if resdata:
                cn = resdata["cn"][0].decode()
                name = resdata.get("displayName", (cn,))[0].decode()
                pname = FC_PROFILE_PREFIX % FC_GLOBAL_POLICY_PROFILE_NAME
                if name.startswith(FC_PROFILE_PREFIX[:-2]) and name != pname:
                    desc = resdata.get("description", (b"",))[0].decode()
                    profiles.append((cn, name[len(FC_PROFILE_PREFIX) - 2 :], desc))
        return profiles

    @connection_required
    def get_profile(self, cn):
        logger.debug("Getting profile %s from AD", cn)
        ldap_filter = "(CN=%s)" % cn
        data = self._get_ldap_profile_data(ldap_filter)
        if data:
            return self._data_to_profile(data)
        return None

    @connection_required
    def get_profile_rule(self, name):
        pass

    @connection_required
    def get_user(self, username):
        base_dn = "CN=Users,%s" % self._get_domain_dn()
        s_filter = "(&(objectclass=user)(CN=%s))" % username
        attrs = ["cn", "objectSid"]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        if len(resultlist) > 0:
            data = resultlist[0]
            return {
                "cn": data[0],
                "username": data[1]["cn"][0],
                "sid": self.get_sid(data[1]["objectSid"][0]),
            }
        return None

    @connection_required
    def get_group(self, groupname):
        base_dn = "%s" % self._get_domain_dn()
        s_filter = "(&(objectclass=group)(CN=%s))" % groupname
        attrs = ["cn", "objectSid"]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        resultlist = [x for x in resultlist if x[0] is not None]
        if len(resultlist) > 0:
            data = resultlist[0]
            return {
                "cn": data[0],
                "groupname": data[1]["cn"][0],
                "sid": self.get_sid(data[1]["objectSid"][0]),
            }
        return None

    @connection_required
    def get_host(self, hostname):
        base_dn = "CN=Computers,%s" % self._get_domain_dn()
        s_filter = "(&(objectclass=computer)(CN=%s))" % hostname
        attrs = ["cn", "objectSid"]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        if len(resultlist) > 0:
            data = resultlist[0]
            return {
                "cn": data[0],
                "hostname": data[1]["cn"][0],
                "sid": self.get_sid(data[1]["objectSid"][0]),
            }
        return None

    def get_object_by_sid(self, sid, classes=["computer", "user", "group"]):
        base_dn = "%s" % self._get_domain_dn()
        object_classes = "".join(["(objectclass=%s)" % x for x in classes])
        s_filter = "(&(|%s)(objectSid=%s))" % (object_classes, sid)
        attrs = ["cn", "objectClass"]
        resultlist = self.connection.search_s(
            base_dn, ldap.SCOPE_SUBTREE, s_filter, attrs
        )
        resultlist = [x for x in resultlist if x[0] is not None]
        if len(resultlist) > 0:
            data = resultlist[0][1]
            return {"cn": data["cn"][0], "objectClass": data["objectClass"]}
        return None

    def get_sid(self, sid_ndr):
        return ndr_unpack(security.dom_sid, sid_ndr)

    def get_domain_sid(self):
        base_dn = "%s" % self._get_domain_dn()
        s_filter = "(objectClass=*)"
        attrs = ["objectSid"]
        resultlist = self.connection.search_s(base_dn, ldap.SCOPE_BASE, s_filter, attrs)
        return self.get_sid(resultlist[0][1]["objectSid"][0])


class SecurityDescriptorHelper:
    def __init__(self, sd, connector):
        self.connector = connector
        self.dacl_flags = ""
        self.dacls = []
        self.sacl_flags = ""
        self.sacls = []
        if isinstance(sd, security.descriptor):
            # Get the SDDL and parse
            sddl = sd.as_sddl()
        else:
            try:
                # Try to unpack data, then get SDDL and parse
                sd = ndr_unpack(security.descriptor, sd)
                sddl = sd.as_sddl()
            except Exception:
                sddl = sd
        self.parse_sddl(sddl)

    def parse_sddl(self, sddl):
        logger.debug("Parsing SDDL for security descriptor. Given SDDL: %s", sddl)
        # SACLs
        if "S:" in sddl:
            sacl_index = sddl.index("S:")
            sacl_data = sddl[sacl_index + 2 :]
            if "(" in sacl_data:
                self.sacl_flags = sacl_data[: sacl_data.index("(")]
                sacl_aces = sacl_data[sacl_data.index("(") :]
                self.sacls = [ACEHelper(x) for x in sacl_aces[1:][:-1].split(")(")]
            else:
                self.sacl_flags = sacl_data
        else:
            sacl_index = len(sddl) - 1
        # DACLs
        if "D:" in sddl:
            dacl_index = sddl.index("D:")
            dacl_data = sddl[dacl_index + 2 : sacl_index]
            if "(" in dacl_data:
                self.dacl_flags = dacl_data[: dacl_data.index("(")]
                dacl_aces = dacl_data[dacl_data.index("(") :]
                self.dacls = [ACEHelper(x) for x in dacl_aces[1:][:-1].split(")(")]
            else:
                self.dacl_flags = dacl_data
        # Group
        g_index = sddl.index("G:")
        self.group_sid = sddl[g_index + 2 : dacl_index]
        logger.debug("SDDL parse finished")
        # Owner
        self.owner_sid = sddl[2:g_index]

    def add_dacl_ace(self, ace):
        logger.debug("Adding ACE to security descriptor: %s")
        if ace not in self.dacls:
            self.dacls.append(ACEHelper(str(ace)))
        else:
            logger.debug("ACE %s already exists for this security descriptor")

    def get_fc_applies(self):
        logger.debug("Getting applies from security descriptor ACEs")
        users = set()
        groups = set()
        hosts = set()

        for ace in self.dacls:
            # Manage GPO object ACEs only
            if ace.object_guid == GPO_APPLY_GROUP_POLICY_CAR:
                # Manage ACEs that apply to an user
                obj = self.connector.get_object_by_sid(ace.account_sid)
                if obj is not None:
                    if "user" in obj["objectClass"]:
                        users.add(obj["cn"])
                    elif "group" in obj["objectClass"]:
                        groups.add(obj["cn"])
                    elif "computer" in obj["objectClass"]:
                        hosts.add(obj["cn"])
        applies = {
            "users": sorted(list(users)),
            "groups": sorted(list(groups)),
            "hosts": sorted(list(hosts)),
            "hostgroups": [],
        }
        logger.debug("Retrieved applies: %s", applies)
        return applies

    def to_sddl(self):
        return "O:%sG:%sD:%sS:%s" % (
            self.owner_sid,
            self.group_sid,
            "%s%s"
            % (
                self.dacl_flags,
                "".join([str(x) for x in self.dacls]),
            ),
            "%s%s"
            % (
                self.sacl_flags,
                "".join([str(x) for x in self.sacls]),
            ),
        )

    def to_sd(self):
        logger.debug("Generating security descriptor")
        sddl = self.to_sddl()
        logger.debug("SDDL for security descriptor generation: %s", sddl)
        domain_sid = self.connector.get_domain_sid()
        sd = security.descriptor.from_sddl(sddl, domain_sid)
        return sd


class ACEHelper:
    __hash__ = None

    def __init__(self, ace_string):
        # Remove parenthesis from ACE string
        ace_string = ace_string.replace("(", "").replace(")", "")
        # Split data
        data = ace_string.split(";")
        self.type = data[0]
        self.flags = data[1]
        self.rights = data[2]
        self.object_guid = data[3]
        self.inherit_object_guid = data[4]
        self.account_sid = data[5]
        # Resource attribute is optional
        if len(data) > 6:
            self.resource_attribute = data[6]
        else:
            self.resource_attribute = None

    @property
    def ace_string(self):
        data = [
            self.type,
            self.flags,
            self.rights,
            self.object_guid,
            self.inherit_object_guid,
            self.account_sid,
        ]
        if self.resource_attribute is not None:
            data.append(self.resource_attribute)
        return "(%s)" % ";".join(data)

    def __eq__(self, other):
        ace_str = str(other)
        return ace_str == self.ace_string

    def __repr__(self):
        return "ACEHelper%s" % self.ace_string

    def __str__(self):
        return self.ace_string
