# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

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
import os
import pickle
import xml.etree.ElementTree as ET

import libvirt

from fleetcommander.database import BaseDBManager, SQLiteDict


def _xmltree_sort(root):
    for el in root.iter():
        attrib = el.attrib
        if len(attrib) > 1:
            attribs = sorted(attrib.items())
            attrib.clear()
            attrib.update(attribs)


def _xmltree_to_string(xml_path):
    tree = ET.parse(xml_path)
    tree = tree.getroot()
    _xmltree_sort(tree)
    return ET.tostring(tree).decode()


# Preload needed files
XML_ORIG = _xmltree_to_string(
    os.path.join(os.environ["TOPSRCDIR"], "tests/data/libvirt_domain-orig.xml")
)

XML_MODIF_HTML5 = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-html5.xml",
    )
)

XML_MODIF_HTML5_DEBUG = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-html5-debug.xml",
    )
)

XML_MODIF_DIRECT = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-direct.xml",
    )
)

XML_MODIF_DIRECT_DEBUG = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-direct-debug.xml",
    )
)

XML_MODIF_DIRECT_PLAIN = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-direct-plain.xml",
    )
)

XML_MODIF_DIRECT_PLAIN_DEBUG = _xmltree_to_string(
    os.path.join(
        os.environ["TOPSRCDIR"],
        "tests/data/libvirt_domain-modified-direct-plain-debug.xml",
    )
)

XML_NO_SPICE = _xmltree_to_string(
    os.path.join(os.environ["TOPSRCDIR"], "tests/data/libvirt_domain-nospice.xml")
)

UUID_ORIGIN = "e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81"
UUID_NO_SPICE = "0999a0ee-a4c4-11e5-b3a5-68f728db19d3"
UUID_TEMPORARY_SPICE_HTML5 = "11111111-722d-45d9-b66c-fefb33235a98"
UUID_TEMPORARY_SPICE_HTML5_DEBUG = "111debug-722d-45d9-b66c-fefb33235a98"
UUID_TEMPORARY_SPICE_DIRECT = "22222222-722d-45d9-b66c-fefb33235a98"
UUID_TEMPORARY_SPICE_DIRECT_DEBUG = "222debug-722d-45d9-b66c-fefb33235a98"
UUID_TEMPORARY_SPICE_DIRECT_PLAIN = "33333333-722d-45d9-b66c-fefb33235a98"
UUID_TEMPORARY_SPICE_DIRECT_PLAIN_DEBUG = "333debug-722d-45d9-b66c-fefb33235a98"


class State(SQLiteDict):
    """
    Libvirtcontrollermock state
    """

    TABLE_NAME = "libvirtmockstate"


class LibvirtModuleMocker:

    db_path = ":memory:"

    VIR_DOMAIN_METADATA_TITLE = 1
    VIR_DOMAIN_XML_SECURE = 1

    @classmethod
    def open(cls, connection_uri):
        # Return a LibvirtConnectionMocker
        LibvirtConnectionMocker.state = State(BaseDBManager(cls.db_path))
        conn = LibvirtConnectionMocker(connection_uri)
        return conn


class LibvirtConnectionMocker(libvirt.virConnect):
    """
    Class for mocking libvirt connection
    """

    def __init__(self, connection_uri):
        self.connection_uri = connection_uri

        if "domains" not in self.state:
            self.state["domains"] = pickle.dumps(
                [
                    LibvirtDomainMocker(XML_ORIG),
                    LibvirtDomainMocker(XML_NO_SPICE),
                    LibvirtDomainMocker(
                        XML_MODIF_HTML5
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_HTML5[:8],
                            "uuid": UUID_TEMPORARY_SPICE_HTML5,
                        }
                    ),
                    LibvirtDomainMocker(
                        XML_MODIF_HTML5_DEBUG
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_HTML5_DEBUG[:8],
                            "uuid": UUID_TEMPORARY_SPICE_HTML5_DEBUG,
                            "runtimedir": "/run/user/1001",
                        }
                    ),
                    LibvirtDomainMocker(
                        XML_MODIF_DIRECT
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_DIRECT[:8],
                            "uuid": UUID_TEMPORARY_SPICE_DIRECT,
                            "runtimedir": "/run/user/1001",
                        }
                    ),
                    LibvirtDomainMocker(
                        XML_MODIF_DIRECT_DEBUG
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_DIRECT_DEBUG[:8],
                            "uuid": UUID_TEMPORARY_SPICE_DIRECT_DEBUG,
                            "runtimedir": "/run/user/1001",
                        }
                    ),
                    LibvirtDomainMocker(
                        XML_MODIF_DIRECT_PLAIN
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_DIRECT_PLAIN[:8],
                            "uuid": UUID_TEMPORARY_SPICE_DIRECT_PLAIN,
                            "runtimedir": "/run/user/1001",
                        }
                    ),
                    LibvirtDomainMocker(
                        XML_MODIF_DIRECT_PLAIN_DEBUG
                        % {
                            "name-uuid": UUID_TEMPORARY_SPICE_DIRECT_PLAIN_DEBUG[:8],
                            "uuid": UUID_TEMPORARY_SPICE_DIRECT_PLAIN_DEBUG,
                            "runtimedir": "/run/user/1001",
                        }
                    ),
                ]
            )

    @property
    def domains(self):
        return pickle.loads(self.state["domains"])

    def listAllDomains(self, flags=0):
        return self.domains

    def createXML(self, xmlDesc, flags=0):
        newdomain = LibvirtDomainMocker(xmlDesc)
        domains = self.domains
        domains.append(newdomain)
        self.state["domains"] = pickle.dumps(domains)
        return newdomain

    def lookupByUUIDString(self, uuidstr):
        for domain in self.domains:
            if domain.UUIDString() == uuidstr:
                return domain
        return None

    def getHostname(self):
        return "localhost"

    def __del__(self):
        pass


class LibvirtDomainMocker:
    """
    Class for mocking libvirt domain
    """

    def __init__(self, xmldata):
        """Autopatching xml, as like it does libvirt."""
        root = ET.fromstring(xmldata)
        # from docs:
        # the address attribute is duplicated as listen attribute in graphics
        # element for backward compatibility. If both are provided they must be
        # equal.
        devs = root.find("devices")
        graphics = devs.find("graphics")
        listen = graphics.find("listen")
        address = listen.get("address")
        graphics.set("listen", address)

        if graphics.get("autoport") == "yes":
            default_mode = graphics.get("defaultMode")
            if default_mode == "insecure":
                graphics.set("port", "5900")
            elif default_mode == "secure":
                graphics.set("tlsPort", "5900")
            else:
                graphics.set("port", "5900")
                graphics.set("tlsPort", "5901")

        # state attribute that reflects whether a process in the guest is active on the
        # channel
        channels = devs.findall("channel")
        for channel in channels:
            channel_type = channel.get("type")
            if channel_type in ("spiceport", "unix"):
                target = channel.find("target")
                if target.get("name") == "org.freedesktop.FleetCommander.0":
                    target.set("state", "disconnected")

        self.domain_name = root.find("name").text
        self.domain_title = root.find("title").text
        self.domain_uuid = root.find("uuid").text
        self.active = True
        self.transient = False

        _xmltree_sort(root)
        self.xmldata = ET.tostring(root).decode()

    def UUIDString(self):
        return self.domain_uuid

    def name(self):
        return self.domain_name

    def XMLDesc(self, flags=0):
        return self.xmldata

    def isActive(self):
        return self.active

    def isPersistent(self):
        return not self.transient

    def metadata(self, element, namespace):
        if (
            namespace is None
            and element == LibvirtModuleMocker.VIR_DOMAIN_METADATA_TITLE
        ):
            return self.domain_title
        raise Exception()

    def destroy(self):
        self.active = False
        if self.transient:
            # Remove from domains list
            pass

    def undefine(self):
        if not self.transient:
            self.transient = True
        else:
            raise Exception("Trying to undefine transient domain")
