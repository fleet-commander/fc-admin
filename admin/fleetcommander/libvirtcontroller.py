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
from __future__ import print_function

from collections import namedtuple

import binascii
import os
import time
import uuid
import xml.etree.ElementTree as ET
import logging

import libvirt

from . import sshcontroller


class LibVirtControllerException(Exception):
    pass


class LibVirtController:
    """
    Libvirt based session controller
    """

    RSA_KEY_SIZE = 2048
    DEFAULT_LIBVIRTD_SOCKET = "$XDG_RUNTIME_DIR/libvirt/libvirt-sock"
    DEFAULT_LIBVIRT_VIDEO_DRIVER = "virtio"
    LIBVIRT_URL_TEMPLATE = "qemu+ssh://%s@%s/%s"
    MAX_SESSION_START_TRIES = 3
    SESSION_START_TRIES_DELAY = 0.1
    MAX_DOMAIN_UNDEFINE_TRIES = 3
    DOMAIN_UNDEFINE_TRIES_DELAY = 0.1
    channel = None
    viewer = None
    _VIDEO_DRIVER_CMD = (
        "if [ -x /usr/libexec/qemu-kvm ]; "
        "then cmd='/usr/libexec/qemu-kvm'; "
        "else cmd='/usr/bin/qemu-kvm'; fi ; "
        "$cmd -device help 2>&1 | grep 'virtio-vga' > /dev/null; "
        "if [ $? == 0 ]; then echo 'virtio'; else echo 'qxl'; fi"
    )
    _SESSION_SOCKET_CMD = (
        "/usr/sbin/libvirtd -d > /dev/null 2>&1; echo {socket} && [ -S {socket} ]"
    )

    def __init__(self, data_path, username, hostname, mode):
        """
        Class initialization
        """
        self._libvirt_socket = ""
        self._libvirt_video_driver = self.DEFAULT_LIBVIRT_VIDEO_DRIVER

        if mode not in ["system", "session"]:
            raise LibVirtControllerException(
                'Invalid libvirt mode selected. Must be "system" or "session"'
            )
        self.mode = mode

        self.home_dir = os.path.expanduser("~")

        # Connection data
        self.username = username
        self.hostname = hostname

        # SSH connection parameters
        if hostname:
            hostport = hostname.split(":")
            if len(hostport) == 1:
                hostport.append(22)
            self.ssh_host, self.ssh_port = hostport

        # libvirt connection
        self.conn = None

        self.data_dir = os.path.abspath(data_path)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.private_key_file = os.path.join(self.data_dir, "id_rsa")
        self.public_key_file = os.path.join(self.data_dir, "id_rsa.pub")
        self.known_hosts_file = os.path.join(self.home_dir, ".ssh/known_hosts")

        self.ssh = sshcontroller.SSHController()

        # generate key if neeeded
        if not os.path.exists(self.private_key_file):
            self.ssh.generate_ssh_keypair(self.private_key_file)

        self._last_started_domain = None
        self._last_stopped_domain = None

        self.session_params = namedtuple(
            "session_params",
            [
                "domain",
                "details",
            ],
        )

    def add_changes_channel(self, parent, name, domain_name, alias=None):
        raise NotImplementedError

    def add_spice_listen(self, parent):
        raise NotImplementedError

    def add_spice_secure(self, elem):
        raise NotImplementedError

    def generate_spice_ticket(self):
        # taken from token_hex (Python3.6+)
        return binascii.hexlify(os.urandom(16)).decode("ascii")

    def _get_libvirt_socket(self):
        # Get Libvirt socket for session mode
        if self.mode == "session":
            logging.debug("libvirtcontroller: " "Getting session mode libvirt socket.")

            try:
                out = self.ssh.execute_remote_command(
                    command=self._SESSION_SOCKET_CMD.format(
                        socket=self.DEFAULT_LIBVIRTD_SOCKET,
                    ),
                    private_key_file=self.private_key_file,
                    username=self.username,
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    UserKnownHostsFile=self.known_hosts_file,
                )
                self._libvirt_socket = out.decode().strip()
                logging.debug(
                    "libvirtcontroller: " "Session mode libvirt socket is %s",
                    self._libvirt_socket,
                )
            except Exception as e:
                raise LibVirtControllerException(
                    "Error connecting to libvirt host: %s" % e
                )
        else:
            logging.debug(
                "libvirtcontroller: "
                "Using system mode. No need to check for libvirt socket."
            )
            self._libvirt_socket = ""

    def _get_libvirt_video_driver(self):
        logging.debug("libvirtcontroller: " "Getting libvirt video driver.")

        try:
            out = self.ssh.execute_remote_command(
                command=self._VIDEO_DRIVER_CMD,
                private_key_file=self.private_key_file,
                username=self.username,
                hostname=self.ssh_host,
                port=self.ssh_port,
                UserKnownHostsFile=self.known_hosts_file,
            )
            self._libvirt_video_driver = out.decode().strip()
            logging.debug(
                "libvirtcontroller: Using %s video driver.", self._libvirt_video_driver
            )
        except Exception as e:
            raise LibVirtControllerException("Error connecting to libvirt host: %s" % e)

    def _prepare_remote_env(self):
        """
        Runs libvirt remotely to execute the session daemon and get needed
        data for connection.
        Also checks for supported video driver to fallback into QXL if needed

        Libvirt connection using qemu+ssh requires socket path for session
        connections.
        """
        logging.debug("libvirtcontroller: Checking remote environment.")
        self._get_libvirt_socket()
        self._get_libvirt_video_driver()
        logging.debug("libvirtcontroller: Ended checking remote environment.")

    def _connect(self):
        """
        Makes a connection to a host using libvirt qemu+ssh
        """
        logging.debug("libvirtcontroller: Connecting to libvirt")
        if self.conn is None:

            # Prepare remote environment
            self._prepare_remote_env()

            logging.debug("libvirtcontroller: Not connected yet. Prepare connection.")

            options = {
                #'known_hosts': self.known_hosts_file,  # Custom known_hosts file to not alter the default one
                "keyfile": self.private_key_file,  # Private key file generated by Fleet Commander
                # 'no_verify': '1',  # Add hosts automatically to  known hosts
                "no_tty": "1",  # Don't ask for passwords, confirmations etc.
                "sshauth": "privkey",
            }

            if self.mode == "session":
                options["socket"] = self._libvirt_socket
            url = self.LIBVIRT_URL_TEMPLATE % (self.username, self.hostname, self.mode)
            connection_uri = "%s?%s" % (
                url,
                "&".join(
                    ["%s=%s" % (key, value) for key, value in sorted(options.items())]
                ),
            )
            try:
                self.conn = libvirt.open(connection_uri)
            except Exception as e:
                raise LibVirtControllerException("Error connecting to host: %s" % e)

            logging.debug("libvirtcontroller: Connected to libvirt host.")
        else:
            logging.debug("libvirtcontroller: Already connected. Reusing connection.")

    def _get_spice_parms(self, domain):
        """
        Obtain spice connection parameters for specified domain
        """
        # Get SPICE uri
        tries = 0
        spice_params = namedtuple(
            "spice_params",
            [
                "port",
                "tls_port",
                "listen",
                "passwd",
            ],
        )

        while True:
            root = ET.fromstring(domain.XMLDesc(libvirt.VIR_DOMAIN_XML_SECURE))
            devs = root.find("devices")
            graphics = devs.find("graphics")
            try:
                if graphics.get("type") == "spice":
                    # listen attribute of graphics itself is deprecated
                    listen = graphics.find("listen")
                    return spice_params(
                        port=graphics.get("port"),
                        tls_port=graphics.get("tlsPort"),
                        listen=listen.get("address"),
                        passwd=graphics.get("passwd"),
                    )
            except Exception:
                pass

            if tries < self.MAX_SESSION_START_TRIES:
                time.sleep(self.SESSION_START_TRIES_DELAY)
                tries += 1
            else:
                raise LibVirtControllerException(
                    "Can not obtain SPICE URI for virtual session"
                )

    def _generate_new_domain_xml(self, xmldata, spice_ticket):
        """
        Generates new domain XML from given XML data
        """
        # Parse XML
        root = ET.fromstring(xmldata)
        # Add QEMU Schema
        root.set("xmlns:qemu", "http://libvirt.org/schemas/domain/qemu/1.0")
        # Add QEMU command line option -snapshot
        cmdline = ET.SubElement(root, "qemu:commandline")
        cmdarg = ET.SubElement(cmdline, "qemu:arg")
        cmdarg.set("value", "-snapshot")
        # Remove blockdev capability for snapshot support
        cpbline = ET.SubElement(root, "qemu:capabilities")
        cpbarg = ET.SubElement(cpbline, "qemu:del")
        cpbarg.set("capability", "blockdev")
        # Change domain UUID
        newuuid = str(uuid.uuid4())
        root.find("uuid").text = newuuid
        # Change domain name
        domain_name = "fc-{}".format(newuuid[:8])
        root.find("name").text = domain_name
        # Change domain title
        try:
            title = root.find("title").text
            root.find("title").text = "%s - Fleet Commander temporary session" % (title)
        except AttributeError:
            pass
        # Remove domain MAC addresses
        devs = root.find("devices")
        for elem in devs.findall("interface"):
            mac = elem.find("mac")
            if mac is not None:
                elem.remove(mac)

        video = devs.find("video")
        model = video.find("model")
        if model is not None:
            video.remove(model)
        model = ET.SubElement(video, "model")
        model.set("heads", "1")
        model.set("primary", "yes")
        model.set("type", self._libvirt_video_driver)
        # Remove all graphics adapters and create our own
        for elem in devs.findall("graphics"):
            devs.remove(elem)
        graphics = ET.SubElement(devs, "graphics")
        graphics.set("type", "spice")
        graphics.set("autoport", "yes")
        graphics.set("passwd", spice_ticket)
        self.add_spice_secure(graphics)
        self.add_spice_listen(graphics)
        self.add_changes_channel(
            devs, "org.freedesktop.FleetCommander.0", domain_name, "fc0"
        )
        return ET.tostring(root).decode()

    def _close_ssh_tunnel(self):
        """
        Close SSH tunnel
        """
        logging.debug("libvirtcontroller: Closing SSH tunnel")

        # Execute SSH and close tunnel
        try:
            self.ssh.close_tunnel(
                self.private_key_file,
                self.username,
                self.ssh_host,
                self.ssh_port,
                UserKnownHostsFile=self.known_hosts_file,
            )
            logging.debug("libvirtcontroller: Tunnel closed")
        except Exception as e:
            raise LibVirtControllerException("Error closing tunnel: %s" % e)

    def _open_ssh_tunnel(self, local_forward, **kwargs):
        """
        Open SSH tunnel for spice port
        """
        logging.debug("libvirtcontroller: Opening SSH tunnel")
        kwargs["UserKnownHostsFile"] = self.known_hosts_file

        # Execute SSH and bring up tunnel
        try:
            self.ssh.open_tunnel(
                local_forward,
                self.private_key_file,
                self.username,
                self.ssh_host,
                self.ssh_port,
                **kwargs,
            )
            logging.debug(
                "libvirtcontroller: Tunnel opened:%s",
                local_forward,
            )
        except Exception as e:
            raise LibVirtControllerException("Error opening tunnel: %s" % e)

    def _undefine_domain(self, domain):
        """
        Undefines a domain waiting to be reported as defined to libVirt
        """
        try:
            persistent = domain.isPersistent()
        except AttributeError:
            return

        if persistent:
            tries = 0
            while True:
                try:
                    domain.undefine()
                    break
                except Exception:
                    pass
                if tries < self.MAX_DOMAIN_UNDEFINE_TRIES:
                    time.sleep(self.DOMAIN_UNDEFINE_TRIES_DELAY)
                    tries += 1
                else:
                    break

    def list_domains(self):
        """
        Returns a dict with uuid and domain name
        """
        logging.debug("libvirtcontroller: Listing domains")
        self._connect()
        logging.debug("libvirtcontroller: Retrieving LibVirt domains")
        domains = self.conn.listAllDomains()

        def domain_name(dom):
            try:
                return dom.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None)
            except Exception as e:
                print(e)
                return dom.name()

        domainlist = [
            {
                "uuid": domain.UUIDString(),
                "name": domain_name(domain),
                "active": domain.isActive(),
                "temporary": domain.name().startswith("fc-"),
            }
            for domain in domains
        ]
        logging.debug("libvirtcontroller: Domains list: %s", domainlist)
        return domainlist

    def session_start(self, identifier):
        """
        Start session in virtual machine
        """
        raise NotImplementedError

    def session_stop(self, identifier):
        """
        Stops session in virtual machine
        """
        logging.debug("libvirtcontroller: Stopping session")
        # Kill ssh tunnel
        try:
            self._close_ssh_tunnel()
        except Exception:
            pass
        self._connect()
        # Get machine by its uuid
        self._last_stopped_domain = self.conn.lookupByUUIDString(identifier)
        # Destroy domain
        self._last_stopped_domain.destroy()
        # Undefine domain
        self._undefine_domain(self._last_stopped_domain)


class LibVirtTlsSpice(LibVirtController):
    SPICE_CA_CERT = "/etc/pki/libvirt-spice/ca-cert.pem"
    SPICE_CERT = "/etc/pki/libvirt-spice/server-cert.pem"

    _XDG_RUNTIMEDIR_CMD = 'echo "$XDG_RUNTIME_DIR"'
    _SPICE_CA_CERT_CMD = "openssl x509 -in {ca}"
    _SPICE_CERT_SUBJ_CMD = (
        "openssl x509 -noout -subject -nameopt oneline -nameopt "
        "-space_eq -in {cert} | sed 's/^subject=//'"
    )

    def __init__(self, data_path, username, hostname, mode):
        super().__init__(data_path, username, hostname, mode)
        self.channel = "unix"
        self.viewer = "spice_remote_viewer"

    def _get_user_runtime_dir(self):
        logging.debug("libvirtcontroller: " "Getting user runtime directory.")

        try:
            out = self.ssh.execute_remote_command(
                command=self._XDG_RUNTIMEDIR_CMD,
                private_key_file=self.private_key_file,
                username=self.username,
                hostname=self.ssh_host,
                port=self.ssh_port,
                UserKnownHostsFile=self.known_hosts_file,
            )
            runtimedir = out.decode().strip()
            logging.debug(
                "libvirtcontroller: " "Receive user runtime dir %s", runtimedir
            )
            if not runtimedir:
                raise LibVirtControllerException(
                    "Variable XDG_RUNTIME_DIR is not set on libvirt host"
                )
            return runtimedir
        except Exception as e:
            raise LibVirtControllerException("Error connecting to libvirt host: %s" % e)

    @property
    def _notify_socket_path(self):
        if not hasattr(self, "__notify_socket_path"):
            user_runtimedir = self._get_user_runtime_dir()
            # pylint: disable=attribute-defined-outside-init
            self.__notify_socket_path = os.path.join(user_runtimedir, "{}.socket")
            # pylint: enable=attribute-defined-outside-init
        return self.__notify_socket_path

    def add_changes_channel(self, parent, name, domain_name, alias=None):
        channel = ET.SubElement(parent, "channel")
        channel.set("type", self.channel)
        source = ET.SubElement(channel, "source")
        source.set("mode", "bind")
        source.set("path", self._notify_socket_path.format(domain_name))
        target = ET.SubElement(channel, "target")
        target.set("type", "virtio")
        target.set("name", name)
        if alias is not None:
            aliaselem = ET.SubElement(channel, "alias")
            aliaselem.set("name", alias)

    def add_spice_listen(self, parent):
        # listen_address = 'localhost'
        self._connect()
        listen_address = self.conn.getHostname()
        listen = ET.SubElement(parent, "listen")
        listen.set("type", "address")
        listen.set("address", listen_address)

    def add_spice_secure(self, elem):
        elem.set("defaultMode", "secure")

    def session_start(self, identifier):
        """
        Start session in virtual machine
        """
        logging.debug("libvirtcontroller: Starting session")
        self._connect()
        # Get machine by its identifier
        origdomain = self.conn.lookupByUUIDString(identifier)
        spice_ticket = self.generate_spice_ticket()

        # Generate new domain description modifying original XML to use qemu -snapshot command line
        newxml = self._generate_new_domain_xml(
            origdomain.XMLDesc(), spice_ticket=spice_ticket
        )

        # Create and run new domain from new XML definition
        self._last_started_domain = self.conn.createXML(newxml)

        # Get spice host and port
        spice_params = self._get_spice_parms(self._last_started_domain)

        # Make sure spice ticket was properly set,
        # for example, 'passwd' field has enough length
        if spice_params.passwd != spice_ticket:
            raise LibVirtControllerException("Error processing spice ticket")

        ca_cert = self._get_spice_ca_cert()
        cert_subject = self._get_spice_cert_subject()

        local_runtime_dir = os.environ["XDG_RUNTIME_DIR"]
        # cockpit will read from
        local_socket = os.path.join(local_runtime_dir, "fc-logger.socket")
        # fc logger will write to
        remote_socket = self._notify_socket_path.format(
            self._last_started_domain.name()
        )
        logging.debug(
            "libvirtcontroller: local user notify socket path: %s", local_socket
        )
        local_forward = "{local_socket}:{remote_socket}".format(
            local_socket=local_socket,
            remote_socket=remote_socket,
        )

        self._open_ssh_tunnel(local_forward, StreamLocalBindUnlink="yes")

        # Make it transient inmediately after started it
        self._undefine_domain(self._last_started_domain)
        details = {
            "host": spice_params.listen,
            "viewer": self.viewer,
            "notify_socket": local_socket,
            "ca_cert": ca_cert,
            "cert_subject": cert_subject,
            "tls_port": spice_params.tls_port,
            "ticket": spice_ticket,
        }

        return self.session_params(
            domain=self._last_started_domain.UUIDString(),
            details=details,
        )

    def _get_spice_ca_cert(self):
        logging.debug(
            "libvirtcontroller: " "Getting SPICE CA certificate for FC TLS session."
        )
        try:
            out = self.ssh.execute_remote_command(
                command=self._SPICE_CA_CERT_CMD.format(ca=self.SPICE_CA_CERT),
                private_key_file=self.private_key_file,
                username=self.username,
                hostname=self.ssh_host,
                port=self.ssh_port,
                UserKnownHostsFile=self.known_hosts_file,
            )
            spice_ca = out.decode().strip()
            logging.debug(
                "libvirtcontroller: " "Receive SPICE CA certificate %s", spice_ca
            )
            return spice_ca
        except Exception as e:
            raise LibVirtControllerException("Error connecting to libvirt host: %s" % e)

    def _get_spice_cert_subject(self):
        logging.debug(
            "libvirtcontroller: "
            "Getting SPICE certificate subject for FC TLS session."
        )

        try:
            out = self.ssh.execute_remote_command(
                command=self._SPICE_CERT_SUBJ_CMD.format(cert=self.SPICE_CERT),
                private_key_file=self.private_key_file,
                username=self.username,
                hostname=self.ssh_host,
                port=self.ssh_port,
                UserKnownHostsFile=self.known_hosts_file,
            )
            cert_subject = out.decode().strip()
            logging.debug(
                "libvirtcontroller: " "Receive SPICE CA certificate %s", cert_subject
            )
            return cert_subject
        except Exception as e:
            raise LibVirtControllerException("Error connecting to libvirt host: %s" % e)


class LibVirtTunnelSpice(LibVirtController):
    def __init__(self, data_path, username, hostname, mode):
        super().__init__(data_path, username, hostname, mode)
        self.channel = "spiceport"
        self.viewer = "spice_html5"

    def add_changes_channel(self, parent, name, domain_name, alias=None):
        channel = ET.SubElement(parent, "channel")
        channel.set("type", self.channel)
        source = ET.SubElement(channel, "source")
        source.set("channel", name)
        target = ET.SubElement(channel, "target")
        target.set("type", "virtio")
        target.set("name", name)
        if alias is not None:
            aliaselem = ET.SubElement(channel, "alias")
            aliaselem.set("name", alias)

    def add_spice_listen(self, parent):
        listen_address = "localhost"
        listen = ET.SubElement(parent, "listen")
        listen.set("type", "address")
        listen.set("address", listen_address)

    def add_spice_secure(self, elem):
        elem.set("defaultMode", "insecure")

    def session_start(self, identifier):
        """
        Start session in virtual machine
        """
        logging.debug("libvirtcontroller: Starting session")
        self._connect()
        # Get machine by its identifier
        origdomain = self.conn.lookupByUUIDString(identifier)
        spice_ticket = self.generate_spice_ticket()

        # Generate new domain description modifying original XML to use qemu
        # -snapshot command line
        newxml = self._generate_new_domain_xml(
            origdomain.XMLDesc(), spice_ticket=spice_ticket
        )

        # Create and run new domain from new XML definition
        self._last_started_domain = self.conn.createXML(newxml)

        # Get spice host and port
        spice_params = self._get_spice_parms(self._last_started_domain)

        local_runtime_dir = os.environ["XDG_RUNTIME_DIR"]
        # cockpit will read from
        local_socket = os.path.join(local_runtime_dir, "fc-logger.socket")
        local_forward = "{local_socket}:{host}:{hostport}".format(
            local_socket=local_socket,
            host=spice_params.listen,
            hostport=spice_params.port,
        )
        self._open_ssh_tunnel(local_forward, StreamLocalBindUnlink="yes")

        # Make it transient inmediately after started it
        self._undefine_domain(self._last_started_domain)
        details = {
            "host": spice_params.listen,
            "path": local_socket,
            "viewer": self.viewer,
            "ticket": spice_ticket,
        }

        return self.session_params(
            domain=self._last_started_domain.UUIDString(),
            details=details,
        )


def controller(viewer_type, data_path, username, hostname, mode):
    viewers = {
        "spice_html5": LibVirtTunnelSpice,
        "spice_remote_viewer": LibVirtTlsSpice,
    }
    if viewer_type not in viewers:
        raise LibVirtControllerException(
            "Unsupported libvirt viewer type. Must be in {}".format(
                ("{}," * len(viewers)).format(*viewers)
            )
        )
    return viewers[viewer_type](data_path, username, hostname, mode)
