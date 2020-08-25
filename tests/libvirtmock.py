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
import sys
import pickle
import xml.etree.ElementTree as ET

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)

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
XML_ORIG = _xmltree_to_string(os.path.join(os.environ['TOPSRCDIR'],
                              'tests/data/libvirt_domain-orig.xml'))

XML_MODIF = _xmltree_to_string(os.path.join(os.environ['TOPSRCDIR'],
                               'tests/data/libvirt_domain-modified.xml'))

XML_NO_SPICE = _xmltree_to_string(os.path.join(os.environ['TOPSRCDIR'],
                                  'tests/data/libvirt_domain-nospice.xml'))

TEST_UUID_SPICE = 'e2e3ad2a-7c2d-45d9-b7bc-fefb33925a81'
TEST_UUID_NO_SPICE = '0999a0ee-a4c4-11e5-b3a5-68f728db19d3'
TEST_UUID_TEMPORARY = '52e32d2a-722d-45d9-b66c-fefb33235a98'


class State(SQLiteDict):
    """
    Libvirtcontrollermock state
    """
    TABLE_NAME = 'libvirtmockstate'


class LibvirtModuleMocker:

    db_path = ':memory:'

    VIR_DOMAIN_METADATA_TITLE = 1

    @classmethod
    def open(cls, connection_uri):
        # Return a LibvirtConnectionMocker
        LibvirtConnectionMocker.state = State(BaseDBManager(cls.db_path))
        conn = LibvirtConnectionMocker(connection_uri)
        return conn


class LibvirtConnectionMocker:
    """
    Class for mocking libvirt connection
    """

    def __init__(self, connection_uri):
        self.connection_uri = connection_uri

        if 'domains' not in self.state:
            self.state['domains'] = pickle.dumps([
                LibvirtDomainMocker(XML_ORIG),
                LibvirtDomainMocker(XML_NO_SPICE),
                LibvirtDomainMocker(XML_MODIF % {
                    'name-uuid': TEST_UUID_TEMPORARY[:8],
                    'uuid': TEST_UUID_TEMPORARY})
            ])

    @property
    def domains(self):
        return pickle.loads(self.state['domains'])

    def listAllDomains(self):
        return self.domains

    def createXML(self, xmldata):
        newdomain = LibvirtDomainMocker(xmldata)
        domains = self.domains
        domains.append(newdomain)
        self.state['domains'] = pickle.dumps(domains)
        return newdomain

    def lookupByUUIDString(self, identifier):
        for domain in self.domains:
            if domain.UUIDString() == identifier:
                return domain
        return None


class LibvirtDomainMocker:
    """
    Class for mocking libvirt domain
    """
    def __init__(self, xmldata):
        root = ET.fromstring(xmldata)
        devs = root.find('devices')
        for elem in devs.findall('graphics'):
            devs.remove(elem)
        graphics = ET.SubElement(devs, 'graphics')
        graphics.set('type', 'spice')
        graphics.set('port', '5900')
        graphics.set('autoport', 'yes')
        graphics.set('listen', '127.0.0.1')
        listen = ET.SubElement(graphics, 'listen')
        listen.set('type', 'address')
        listen.set('address', '127.0.0.1')
        self.domain_name = root.find('name').text
        self.domain_title = root.find('title').text
        self.domain_uuid = root.find('uuid').text
        self.active = True
        self.transient = False
        _xmltree_sort(root)
        self.xmldata = ET.tostring(root).decode()

    def UUIDString(self):
        return self.domain_uuid

    def name(self):
        return self.domain_name

    def XMLDesc(self):
        return self.xmldata

    def isActive(self):
        return self.active

    def isPersistent(self):
        return not self.transient

    def metadata(self, element, namespace):
        if namespace is None and element == LibvirtModuleMocker.VIR_DOMAIN_METADATA_TITLE:
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
            raise Exception('Trying to undefine transient domain')
