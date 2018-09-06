#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2012 Red Hat, Inc.
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
#          Matthew Barnes <mbarnes@redhat.com>
#          Oliver Gutierrez <ogutierrez@redhat.com>


# Python imports
from __future__ import absolute_import
from __future__ import print_function
import os
import sys
import getopt
import logging
import argparse
import json
import dbus

from dbus.mainloop.glib import DBusGMainLoop
from six.moves import range
DBusGMainLoop(set_as_default=True)

# GObject Introspection imports
import gi

gi.require_version('NM', '1.0')

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import NM


# Python 2 compat
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class RemoteConnectionWorkaround(object):
    def __init__(self, proxy):
        self.proxy = proxy

    def to_dbus(self, flag):
        return self.proxy.call_sync(
            'GetSettings',
            None,
            Gio.DBusCallFlags.NONE,
            3000,
            None).get_child_value(0)

    def get_connection_type(self):
        return self.to_dbus(None).lookup_value(
            'connection', None).lookup_value(
                'type', None).get_string()

    def get_secrets(self, setting, cancellable):
        return self.proxy.call_sync(
            'GetSecrets',
            setting,
            Gio.DBusCallFlags.NONE,
            3000,
            None)


class SpicePortManager(object):
    """
    SPICE port manager class
    """

    DEFAULT_SPICE_CHANNEL_DEV = "/dev/virtio-ports/org.freedesktop.FleetCommander.0"

    def __init__(self, path=DEFAULT_SPICE_CHANNEL_DEV, retry_interval=1000):
        logging.debug("Initializing SPICE port manager")

        self.path = path
        self.retry_interval = retry_interval

        logging.debug(
            "SPICE Port: Using %s for submitting changes" % self.path)

        self.queue = []
        self.timeout = 0

        try:
            self.fd = open(self.path, 'wb', 0)
        except FileNotFoundError as e:
            logging.error('Can\'t open device file %s. Use -n or --no-dev for non Fleet Commander VM session' % self.path)
            sys.exit(1)

    def _perform_submits(self):
        if len(self.queue) < 1:
            return False

        logging.debug("SPICE Port: Performing changes submission")

        while len(self.queue) > 0:
            elem = self.queue.pop(0)
            payload = json.dumps(elem)
            logging.debug("SPICE Port: Submitting change %s" % payload)
            self.fd.write(payload.encode())

        GLib.source_remove(self.timeout)
        self.timeout = 0
        return True

    def submit_change(self, namespace, data):
        logging.debug(
            "Submitting changeset as namespace %s: %s" % (namespace, data))

        self.queue.append({"ns": namespace, "data": data});

        if len(self.queue) > 0 and self.timeout < 1:
            self.timeout = GLib.timeout_add(
                self.retry_interval,
                self._perform_submits)

    def give_up(self):
        self._perform_submits()


class ScreenSaverInhibitor(object):
    """
    Screensaver inhibitor class
    """
    BUS_NAME = "org.freedesktop.ScreenSaver"
    OBJECT_PATH = "/org/freedesktop/ScreenSaver"
    INTERFACE_NAME = "org.freedesktop.ScreenSaver"

    def __init__(self):
        proxy = dbus.SessionBus().get_object(
            self.BUS_NAME, self.OBJECT_PATH)
        self.iface = dbus.Interface(
            proxy, dbus_interface=self.INTERFACE_NAME)
        self.cookie = None
        self.inhibit()

    def inhibit(self):
        """
        Inhibits the screensaver for current session
        """
        logging.debug("Screensaver Inhibitor: Inhibiting screen saver")
        if self.cookie is not None:
            logging.debug("Screensaver Inhibitor: Already inhibited")
            return

        try:
            self.cookie = self.iface.Inhibit(
                'org.freedesktop.FleetCommander.Logger',
                'Preventing Screen locking while Fleet Commander Logger runs')

        except Exception as e:
            logging.error(
                "Screensaver Inhibitor: Error inhibiting screensaver: %s" % e)

    def uninhibit(self):
        """
        Uninhibits the screensaver for current session
        """
        logging.debug("Screensaver Inhibitor: Uninhibiting screen saver");
        try:
            self.iface.UnInhibit(self.cookie)

        except Exception as e:
            logging.error(
                "Screensaver Inhibitor: Error uninhibiting screensaver: %s" % e)
        self.cookie = None


class GSettingsLogger(object):

    BUS_NAME = 'ca.desrt.dconf'
    OBJECT_PATH = '/ca/desrt/dconf/Writer/user'
    INTERFACE_NAME = 'ca.desrt.dconf.Writer'
    LIBREOFFICE_DCONF_PATH = ".config/libreoffice/dconfwrite"

    def __init__(self, connmgr, homedir=GLib.get_home_dir()):
        logging.debug("Constructing GSettingsLogger")

        self._testing_loop = None

        self.homedir = homedir
        self.connmgr = connmgr
        self.path_to_known_schema = {}
        self.relocatable_schemas = []
        self.past_keys_for_path = {}
        self.found_schemas_for_path = {}
        self.dconf_subscription_id = 0

        self.schema_source = Gio.SettingsSchemaSource.get_default()

        # Create file for LibreOffice dconf writes
        dconfwrite = Gio.File.new_for_path(
            os.path.join(self.homedir, self.LIBREOFFICE_DCONF_PATH))

        if not dconfwrite.query_exists(None):
            GLib.mkdir_with_parents(dconfwrite.get_parent().get_path(), 483)
            try:
                dconfwrite.create(Gio.FileCreateFlags.NONE, None)
            except Exception as e:
                logging.error(
                    "Could not create file %s: %s" % (
                        dconfwrite.get_path(), e))

        # Populate a table of paths to schema ids.  We can do this up
        # front for fixed-path schemas.  For relocatable schemas we have to
        # wait for a change to occur and then try to derive the schema from
        # the path and key(s) in the change notification.
        logging.debug("Caching known schemas")
        for schema_name in Gio.Settings.list_schemas():
        #for schema_name in self.schema_source.list_schemas(True):
            schema = self.schema_source.lookup(schema_name, True)
            path = schema.get_path()
            logging.debug("Adding schema %s: %s" % (path, schema_name))
            self.path_to_known_schema[path] = schema_name

        self.relocatable_schemas = Gio.Settings.list_relocatable_schemas()

        Gio.bus_watch_name(
            Gio.BusType.SESSION,
            self.BUS_NAME,
            Gio.BusNameWatcherFlags.NONE,
            self._bus_name_appeared_cb,
            self._bus_name_disappeared_cb)


    def _writer_notify_cb(
            self, connection, sender_name, object_path,
            interface_name, signal_name, parameters, what):
        # Added what parametwe because it gets 8 nor 7 parms
        path = parameters.get_child_value(0).get_string()
        keys = []
        tag  = parameters.get_child_value(2).get_string()
        if not path.endswith("/"):
            split = path.split("/")
            keys.append(split.pop())
            path = "/".join(split) + "/"
        else:
            keys_variant = parameters.get_child_value(1)
            for i in range(keys_variant.n_children()):
                keys.append(keys_variant.get_child_value(i).get_string())
                #keys.append(keys_variant.get_child_value(i).get_string())
        schema_known = False

        logging.debug("dconf Notify: %s" % path)
        logging.debug(">>> Keys: %s" % keys)

        if path.startswith("/org/libreoffice/registry"):
            logging.debug(">>> LibreOffice configuration change detected, no schema search needed")
            self._libreoffice_change(path, keys)
            return

        if path in self.path_to_known_schema:
            schema = self.schema_source.lookup(
                self.path_to_known_schema[path], True)
            settings = Gio.Settings.new_full(schema, None, None)
            self._settings_changed(schema, settings, keys)
            return

        logging.debug(">>> Schema not known yet")
        schema_name = self._guess_schema(path, keys)
        if schema_name is None:
            if self._testing_loop:
                self._testing_loop.quit()
            return

        schema = self.schema_source.lookup(schema_name, True)
        settings = Gio.Settings.new_full (schema, None, path)
        self._settings_changed(schema, settings, keys)

    def _libreoffice_change(self, path, keys):
        logging.debug(
            "Submitting LibreOffice change for keys [%s] for path %s" % (
                keys, path))

        for key in keys:
            command = ["dconf", "read", path + key]
            dconf = Gio.Subprocess.new(
                command, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
            stdout_pipe = dconf.get_stdout_pipe()
            dconf.wait(None)
            if dconf.get_exit_status() != 0:
                logging.error(
                    "Error calling dconf subprocess with arguments: %s" % command)
                return

            # FIXME: libdconf doesn't have introspection support, we call dconf manually
            data = Gio.DataInputStream.new (stdout_pipe)
            variant_string = data.read_until ("\0", None)[0]

            if variant_string == None:
                printerr ("There was an error reading dconf key " + path + key)
                return

            if variant_string.endswith("\n"):
                variantstring = variant_string[:-1]

            variant = None
            try:
                variant = GLib.Variant.parse(None, variant_string, None, None)
            except Exception as e:
                logging.error(
                    "There was an error parsing the variant string from the \
                        dconf read output for '%s%s':" % (path, key))
                logging.error(variant_string)
                return

            finaldata = json.dumps({
                "key": path + key,
                "value": variant.print_(True),
                "signature": variant.get_type_string(),
            }, sort_keys=True)

            self.connmgr.submit_change ("org.libreoffice.registry", finaldata)

        if self._testing_loop is not None:
            self._testing_loop.quit()

    def _settings_changed(self, schema, settings, keys):
        logging.debug(
            "Submitting change for keys ['%s'] on schema %s" % (
                keys, schema.get_id()))

        for key in keys:
            variant = settings.get_value(key)

            data = json.dumps({
                "key": settings.get_property("path") + key,
                "schema": schema.get_id(),
                "value": variant.print_(True),
                "signature": variant.get_type().dup_string(),
            }, sort_keys=True)

            self.connmgr.submit_change("org.gnome.gsettings", data)

        if self._testing_loop is not None:
            self._testing_loop.quit()


    def _guess_schema(self, path, keys):
        """
        In this function we try to guess the schema by trying to find a
        unique candidate that has all the keys that affect a given path.

        We could vastly improve this function if we had DConf bindings
        to list all the keys in a given path outside of GSettings
        """

        if path in self.found_schemas_for_path:
            schema = self.found_schemas_for_path[path]
            logging.debug(
                "Schema for path %s was already found: %s" % (path, schema))
            return schema

        # We store (path,keys) we didn't find a schema for in case
        # future keys might help complete the picture and allows us
        # to find a schema.
        if path in self.past_keys_for_path:
            self.past_keys_for_path[path].extend(keys)
            keys = self.past_keys_for_path[path]

        candidates = []
        for schema_name in self.relocatable_schemas:
            logging.debug("Checking match with schema %s" % schema_name)
            schema = self.schema_source.lookup(schema_name, True)
            if schema is not None:
                key_eval = [key in schema for key in keys]
                if False not in key_eval:
                    logging.debug("Schema %s is a valid candidate" % schema_name)
                    candidates.append(schema_name)

        if len(candidates) == 1:
            # Keep the schema for this path around and discard its keys array
            # from the past_keys_for_path object as we don't need it anymore
            self.found_schemas_for_path[path] = candidates[0]
            if path in self.past_keys_for_path:
                del(self.past_keys_for_path[path])
            logging.debug("Schema found: %s" % candidates[0])
            return candidates[0]

        if len(candidates) > 1:
            logging.debug("Too many schemas match this keyset: %s" % candidates)
        else:
            logging.debug("No schemas with this key were found")

        # We keep all the keys for future attempts
        self.past_keys_for_path[path] = keys

        return None

    def _bus_name_appeared_cb(self, connection, name, owner):
        logging.debug("%s bus appeared" % self.BUS_NAME)
        self.dconf_subscription_id = connection.signal_subscribe(
            owner,
            self.INTERFACE_NAME,
            'Notify',
            self.OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._writer_notify_cb,
            None)
        logging.debug(
            "Subscribed to signal 'Notify'. Subscription ID: %s" % self.dconf_subscription_id)

    def _bus_name_disappeared_cb(self, connection, bus_name):
        logging.debug("%s bus dissapeared" % self.BUS_NAME)
        if self.dconf_subscription_id == 0:
            return
        connection.signal_unsubscribe(self.dconf_subscription_id)
        logging.debug(
            "Unsubscribed from signal 'Notify'. Subscription ID: %s" % self.dconf_subscription_id)
        self.dconf_subscription_id = 0


class NMLogger(object):

    BUS_NAME = "org.freedesktop.NetworkManager"
    OBJECT_PATH = "/org/freedesktop/NetworkManager/Settings"
    INTERFACE_NAME = "org.freedesktop.NetworkManager.Settings"

    def __init__(self, connmgr):
        logging.debug("Constructing NetworkManager logger")
        self.connmgr = connmgr
        logging.debug("Connecting client signal for connection added callback")
        self.nmclient = NM.Client()
        #self.nmclient.connect('connection-added', self.connection_added_cb)

        # self.proxy = dbus.SystemBus().get_object(
        #     self.BUS_NAME, self.OBJECT_PATH)
        # self.iface = dbus.Interface(
        #     self.proxy, dbus_interface=self.INTERFACE_NAME)
        # self.iface.connect_to_signal('NewConnection', self.new_connection_cb)

        self.dbus_conn = Gio.bus_get_sync(Gio.BusType.SYSTEM)

        subs_id = self.dbus_conn.signal_subscribe(
            self.BUS_NAME,
            self.INTERFACE_NAME,
            'NewConnection',
            self.OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self.new_connection_cb,
            None)

    def security_filter(self, conn):
        conn = self.filter_variant(conn, ['connection', 'permissions'])
        conn = self.filter_variant(conn, ['vpn','data','secrets','Xauth password'])
        conn = self.filter_variant(conn, ['vpn','data','secrets','password'])
        conn = self.filter_variant(conn, ['802-1x','password'])
        conn = self.filter_variant(conn, ['802-11-wireless-security','leap-password'])
        return conn

    def filter_variant(self, variant, filters):
        logging.debug("Filtering: %s" % filters)
        is_variant = variant.get_type_string () == "v"

        if is_variant:
            variant = variant.get_child_value(0)

        dict_type = GLib.VariantType("a{s*}")

        if len(filters) < 1 or \
                not variant.is_of_type(dict_type) or \
                variant.n_children() < 1 or \
                variant.lookup_value(filters[0], None) is None:
            if is_variant:
                return GLib.Variant("v", variant)
            return variant

        dic = GLib.VariantBuilder.new(variant.get_type())
        for i in range(variant.n_children()):
            child = variant.get_child_value(i)
            key = child.get_child_value(0).get_string()
            if key != filters[0]:
                dic.add_value(child)
                continue

            if len(filters) == 1:
                continue

            child_builder = GLib.VariantBuilder.new(child.get_type())
            child_builder.add_value(child.get_child_value(0))
            child_builder.add_value(
                self.filter_variant(child.get_child_value(1), filters[1:]))
                #self.filter_variant(child.get_child_value(1), filters.slice(1)))
            dic.add_value(child_builder.end())

        if is_variant:
            return GLib.Variant("v", dic.end())

        ended = dic.end()
        return ended

    def merge_variants(self, va, vb):
        logging.debug("Merging variants")

        are_variants = va.get_type_string() == "v" and \
            vb.get_type_string() == "v"

        if are_variants:
            va = va.get_child_value(0)
            vb = vb.get_child_value(0)

        if va.get_type_string() != vb.get_type_string():
            logging.error("Can't merge variants of different types")
            if are_variants:
                return GLib.Variant("v", va)
            return va

        dict_type = GLib.VariantType("a{s*}")

        if not va.is_of_type(dict_type):
            if are_variants:
                return GLib.Variant("v", vb)
            return vb

        builder = GLib.VariantBuilder.new(va.get_type())
        for i in range(va.n_children()):
            child_a = va.get_child_value(i)
            # key = child_a.get_child_value(0).get_string()[0]
            key = child_a.get_child_value(0).get_string()
            value_b = vb.lookup_value(key, None)
            if value_b is None:
                builder.add_value(child_a)
                continue

            value_a = va.lookup_value(key, None)
            merge = self.merge_variants(value_a, value_b)

            child_builder = GLib.VariantBuilder.new(child_a.get_type())
            child_builder.add_value(child_a.get_child_value(0))
            if child_a.get_child_value(1).get_type_string() == "v" and \
                    merge.get_type_string() != "v":
                merge = GLib.Variant("v", merge)
            child_builder.add_value(merge)
            builder.add_value (child_builder.end())

        for i in range(vb.n_children()):
            child = vb.get_child_value(i)
            key = child.get_child_value(0).get_string()

            if va.lookup_value(key, None) is not None:
                continue;

            builder.add_value (child)

        if are_variants:
            return GLib.Variant("v", builder.end())
        return builder.end()

    # def submit_connection(self, proxy):
    def submit_connection(self, conn):
        logging.debug("Submitting Network Manager connection")

        conf = conn.to_dbus(NM.ConnectionSerializationFlags.ALL)
        conntype = conn.get_connection_type()
        secrets = []

        logging.debug("Added connection of type %s" % conntype)

        if conntype == "802-11-wireless":
            # Looks like this triggers an infinite loop
            try:
                secrets.append(conn.get_secrets("802-11-wireless-security"))
            except Exception:
                pass
            try:
                # we might not want this, ever
                secrets.append(conn.get_secrets("802-1x", None))
            except Exception:
                pass
        elif conntype == "vpn":
            try:
                secrets.append(conn.get_secrets("vpn", None))
            except Exception:
                pass
        elif conntype == "802-3-ethernet":
            try:
                # we might not want this, ever
                secrets.append(conn.get_secrets("802-1x", None))
            except Exception:
                pass
        else:
            logging.debug(
                "Network Connection discarded. Type %s is not supported" % conntype)
            return

        for s in secrets:
            conf = self.merge_variants(conf, s)

        conf = self.security_filter(conf)
        payload = {
          "data": conf.print_(True),
          "uuid": None,
          "type": None,
          "id": None,
        }

        connection = conf.lookup_value("connection", None)
        if connection is not None:
            payload['uuid'] = connection.lookup_value("uuid", None).get_string()
            payload['type'] = connection.lookup_value("type", None).get_string()
            payload['id'] = connection.lookup_value("id", None).get_string()

        self.connmgr.submit_change(
            "org.freedesktop.NetworkManager", json.dumps(payload))

    def deep_unpack(self, variant):
        """
        This is a workaround for the broken deep_unpack behaviour
        TODO: Chck if this is necessary
        """
        def unpack_internal(unpack):
            if instanceof(unpack, GLib.Variant):
                return unpack_internal(unpack.deep_unpack())
            if instanceof(unpack, list) or instanceof(unpack, dict):
                for e in unpack:
                    unpack[e] = unpack_internal(unpack[e])
            return unpack

        return unpack_internal(variant)

    def merge_confs(self, conf, secrets):
        if not instanceof(conf, dict) or not instanceof(secrets, dict):
            logging.error(
                "ERROR: Cannot merge two items that aren't objects: %s %s" % (
                    conf, secrets))
            return {}

        logging.debug(
            "Merging %s and %s" % (json.dumps(conf), json.dumps(secrets)))

        for group in secrets:
            if not group in conf:
                conf[group] = secrets[group]
                continue

            for key in secrets[group]:
                if instanceof(conf[group][key], dict):
                    conf[group][key] = self.merge_confs(conf[group][key],
                        secrets[group][key])
                    continue
                conf[group][key] = secrets[group][key]
        return conf

    # def connection_added_cb(self, client, connection):
    #     """
    #     Connection added
    #     """
    #     logging.debug("Network Manager connection added")
    #     self.submit_connection(connection)

    def new_connection_cb(
            self, connection, sender_name, object_path,
            interface_name, signal_name, parameters, what):
        """
        Connection added
        """
        logging.debug("Network Manager connection added")

        conn_path = parameters.get_child_value(0).get_string()

        proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            self.BUS_NAME,
            conn_path,
            self.INTERFACE_NAME + '.Connection',
            None)

        # FIXME: BUG connection = self.nmclient.get_connection_by_path(conn_path)
        connection = RemoteConnectionWorkaround(proxy)
        self.submit_connection(connection)

class ChromiumLogger(object):
    """
    Chromium log target class
    """

    def __init__(
            self,
            connmgr,
            datadir=GLib.getenv("HOME") + "/.config/chromium",
            namespace="org.chromium.Policies"):

        logging.debug(
            "Initializing chromium logger with namespace %s at %s" % (
                namespace, datadir))

        self.connmgr = connmgr
        self.datadir = datadir
        self.namespace = namespace
        self.local_state_path = self.datadir + "/Local State";
        self.monitored_preferences = {}
        self.initial_bookmarks = {}
        self.monitored_bookmarks = {}
        self.bookmarks_paths = []
        self.file_monitors = {}

        # Load policy map
        self.policy_map = self.load_policy_map()
        if self.policy_map is None:
            logging.error(
                "WARNING: ChromiumLogger can't locate policies file. Chromium/Chrome disabled.")
            return

        # Setup file monitoring for local state
        self._setup_local_state_file_monitor()

    def submit_config_change(self, k, v):
        payload = {
            "key": k,
            "value": v
        }
        self.connmgr.submit_change(self.namespace, json.dumps(payload))

    def load_policy_map(self):
        """
        Load policy list file
        """
        policy_map = None
        for dirpath in GLib.get_system_data_dirs():
            logging.debug("Looking for chromium policies file at %s" % dirpath)
            filepath = os.path.join(dirpath, 'fleet-commander-logger/fc-chromium-policies.json')
            try:
                with open(filepath, 'r') as fd:
                    contents = fd.read()
                    policy_map = json.loads(contents)
                    fd.close()
                logging.debug('Loaded chromium policies file at %s' % filepath)
                break
            except Exception as e:
                logging.debug('Can not open chromium policies file at %s: %s' % (filepath, e))
        return policy_map

    def _setup_local_state_file_monitor(self):
        """
        Load local state file and set a file monitor on it
        """
        local_state_file = Gio.File.new_for_path(self.local_state_path)
        self._local_state_file_updated(None, local_state_file, None, None);
        monitor = local_state_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitors[self.local_state_path] = monitor
        monitor.connect("changed", self._local_state_file_updated)

    def _setup_preferences_file_monitor(self, prefs_path):
        prefs_file = Gio.File.new_for_path(prefs_path)
        if prefs_file.query_exists(None):
            logging.debug(
                "Reading initial information from preferences file %s" % prefs_path)
            prefs = json.loads(
                Gio.File.new_for_path(prefs_path).load_contents(None)[1])
            self.monitored_preferences[prefs_path] = prefs
        else:
            logging.debug("Preferences file at %s does not exist (yet)" % prefs_path)
            self.monitored_preferences[prefs_path] = {}
        logging.debug("Setting up file monitor at %s" % prefs_path)
        monitor = prefs_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitors[prefs_path] = monitor
        monitor.connect("changed", self._preferences_file_updated)

    def _setup_bookmarks_file_monitor(self, bmarks_path):
        bmarks_file = Gio.File.new_for_path(bmarks_path)
        if bmarks_file.query_exists(None):
            logging.debug("Reading initial information from bookmarks file %s" % bmarks_path)
            bmarks = json.loads(
                Gio.File.new_for_path(bmarks_path).load_contents(None)[1])
            self.initial_bookmarks[bmarks_path] = self.parse_bookmarks(bmarks)
        else:
            logging.debug("Bookmarks file at %s does not exist (yet)" % bmarks_path)
            self.initial_bookmarks[bmarks_path] = [];
        logging.debug("Setting up file monitor at %s" % bmarks_path);
        monitor = bmarks_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitors[bmarks_path] = monitor
        monitor.connect("changed", self._bookmarks_file_updated)

    def get_preference_value(self, prefs, preference):
        # Split preference by dot separator
        prefpath = preference.split('.')
        current = prefs;
        for item in prefpath:
            try:
                # Get value from preferences
                current = current[item];
            except Exception as e:
                # Preference is not in preferences data
                return None
        return current

    def _local_state_file_updated(self, monitor, fileobj, otherfile, eventType):
        path = fileobj.get_path()
        logging.debug("Local state file %s changed. %s %s %s %s" % (
            path, monitor, fileobj, otherfile, eventType))
        if eventType == Gio.FileMonitorEvent.CHANGES_DONE_HINT or eventType is None:
            if eventType == None:
                logging.debug("Reading local state file %s" % path)
            if fileobj.query_exists(None):
                # Read local state file data
                data = json.loads(fileobj.load_contents(None)[1])
                # Get currently running sessions
                sessions = data['profile']['last_active_profiles']
                for session in sessions:
                    prefs_path = os.path.join(
                        self.datadir, session, "Preferences")
                    bmarks_path = os.path.join(
                        self.datadir, session, "Bookmarks")
                    if not prefs_path in self.monitored_preferences:
                        logging.debug("New session %s started" % session)
                        # Preferences monitoring
                        logging.debug("Monitoring session preferences file at %s" % prefs_path)
                        # Add file monitoring to preferences file
                        self._setup_preferences_file_monitor(prefs_path)
                        # Add file monitoring to bookmarks file
                        self._setup_bookmarks_file_monitor(bmarks_path)
            else:
                logging.debug("Local state file %s is not present (yet)" % path)

    def _preferences_file_updated(self, monitor, fileobj, otherfile, eventType):
        path = fileobj.get_path()
        logging.debug(
            "Preference file %s notifies changes done hint. %s %s %s %s" % (
                path, monitor, fileobj, otherfile, eventType))
        if eventType == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            if fileobj.query_exists(None):
                prefs = json.loads(fileobj.load_contents(None)[1]);
                logging.debug("PREV: %s" % self.monitored_preferences[path])
                logging.debug("NEW: %s" % prefs)
                for preference in self.policy_map:
                    value = self.get_preference_value(prefs, preference);
                    if value != None:
                        logging.debug("Checking preference %s with value %s" % (
                            preference, value))
                        prev = self.get_preference_value(self.monitored_preferences[path], preference)
                        if preference in self.monitored_preferences[path]:
                            prev = self.monitored_preferences[path][preference];
                        logging.debug(
                            "%s = %s (previous: %s)" % (preference, value, prev))
                        if value != prev:
                            # Submit this config change
                            policy = self.policy_map[preference]
                            logging.debug(
                                "Submitting %s = %s" % (preference, value))
                            self.submit_config_change(policy, value)
                        self.monitored_preferences[path][preference] = value
            else:
                logging.debug(
                    "Preferences file %s is not present (yet)" % path)


    def _bookmarks_file_updated(self, monitor, file, otherfile, eventType):
        if eventType == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            if file.query_exists(None):
                path = file.get_path()
                logging.debug(
                    "Bookmarks file %s notifies changes done hint. %s %s %s %s" % (
                        path, monitor, file, otherfile, eventType))
                bookmarks = self.parse_bookmarks(
                    json.loads(file.load_contents(None)[1]))
                diff = self.get_modified_bookmarks(
                    self.initial_bookmarks[path], bookmarks)
                deploy = self.deploy_bookmarks(diff)
                self.monitored_bookmarks[path] = deploy
                # Append all sessions
                bookmarks_data = []
                print("MONITORED:", self.monitored_bookmarks)
                for session, bmarks in sorted(self.monitored_bookmarks.items()):
                    logging.debug("Appending bookmarks from session %s" % session)
                    bookmarks_data.extend(bmarks)
                self.submit_config_change("ManagedBookmarks", bookmarks_data)
            else:
                logging.debug(
                    "Bookmarks file %s updated but does not exist. Skipping." % path)


    def parse_bookmarks(self, bookmarks):
        flattened_bookmarks = []
        for root in bookmarks["roots"]:
            parsed = self.parse_bookmarks_tree([], bookmarks["roots"][root])
            flattened_bookmarks.extend(parsed)
        return flattened_bookmarks;


    def parse_bookmarks_tree(self, path, leaf):
        if leaf["type"] == "folder":
            nextpath = path[:]
            nextpath.append(leaf["name"])
            logging.debug("Processing bookmarks path %s" % nextpath)
            children = []
            for child in leaf["children"]:
                children.extend(self.parse_bookmarks_tree(nextpath, child))
            return children
        elif leaf["type"] == "url":
            logging.debug("Parsing bookmarks leaf %s" % leaf["name"]);
            return [
                json.dumps([path, leaf["id"], leaf["url"], leaf["name"]])]

    def get_modified_bookmarks(self, bmarks1, bmarks2):
        diff = bmarks2[:]
        for bmark in bmarks1:
            if bmark in diff:
                diff.remove(bmark)
        logging.debug("Previous bookmarks: %s" % bmarks1)
        logging.debug("Modified bookmarks: %s" % bmarks2)
        logging.debug("Difference bookmarks: %s" % diff)
        return diff

    def deploy_bookmarks(self, bookmarks):
        def insert_object(data, path, url, name):
            logging.debug(
                'Inserting bookmark %s (%s) at %s' % (name, url, path))
            if path != []:
                children = data
                for elem in path:
                    logging.debug("Checking path %s" % elem)
                    found = False
                    for child in children:
                        if child['name'] == elem:
                            children = child['children'];
                            found = True
                            break
                    if not found:
                        folder = {'name': elem, 'children': []}
                        children.append(folder)
                        children = folder["children"]
                children.append({'name': name, 'url': url})
            else:
                data.append({'name': name, 'url': url})

        deploy = []
        for bookmark in bookmarks:
            obj = json.loads(bookmark)
            insert_object(deploy, obj[0][1:], obj[2], obj[3])
        return deploy


class ChromeLogger(ChromiumLogger):
    """
    Chrome log target class
    """
    def __init__(
            self,
            connmgr,
            datadir=GLib.getenv("HOME") + "/.config/google-chrome",
            namespace="com.google.chrome.Policies"):
        super(ChromeLogger, self).__init__(connmgr, datadir, namespace)


class FirefoxLogger(object):
    def __init__(
        self,
        connmgr,
        datadir=GLib.get_home_dir() + "/.mozilla/firefox",
        namespace="org.mozilla.firefox"):

        logging.debug(
            "Initializing firefox logger with namespace %s at %s" % (
                namespace, datadir))

        self.connmgr = connmgr
        self.datadir = datadir
        self.namespace = namespace
        self.profiles_path = self.datadir + '/profiles.ini'

        self.monitored_preferences = {}
        self.file_monitors = {}

        # Testing facilities
        self.default_profile_initialized = False
        self.test_profiles_file_updated = False
        self.default_profile_prefs_initialized = False
        self.test_prefs_file_updated = False

        logging.debug(
            "Constructing FirefoxLogger with data directory %s" % self.datadir)

        self.connmgr = connmgr

        # Monitor profiles file
        self._setup_profiles_file_monitor()

    def submit_config_change(self, k, v):
        payload = {
            "key": k,
            "value": v
        }
        self.connmgr.submit_change(
            self.namespace, json.dumps(payload, sort_keys=True))

    def _setup_profiles_file_monitor(self):
        # Set a file monitor on profiles file
        profiles_file = Gio.File.new_for_path(self.profiles_path)
        self._profiles_file_updated(None, profiles_file, None, None)
        if not self.default_profile_initialized:
            monitor = profiles_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.file_monitors[self.profiles_path] = monitor
            monitor.connect("changed", self._profiles_file_updated)

    def _setup_preferences_file_monitor(self, prefs_path):
        if prefs_path not in self.monitored_preferences:
            logging.debug(
                "Setting up file monitoring on %s" % prefs_path)
            prefs_file = Gio.File.new_for_path(prefs_path)
            self._preferences_file_updated(None, prefs_file, None, None)
            logging.debug("Creating file monitor for %s" % prefs_path)
            monitor = prefs_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.file_monitors[prefs_path] = monitor
            monitor.connect("changed", self._preferences_file_updated)
        else:
            logging.debug(
                "File monitoring on %s already set up. Ignoring." % prefs_path)


    def _profiles_file_updated(self, monitor, fileobj, otherfile, eventType):
        if eventType == Gio.FileMonitorEvent.CHANGES_DONE_HINT or eventType is None:
            path = fileobj.get_path()
            if eventType is None:
                logging.debug("Reading Firefox profile file %s" % path)
            else:
                logging.debug(
                    "Firefox profile file %s changed. %s %s %s %s" % (
                        path, monitor, fileobj, otherfile, eventType))
            if fileobj.query_exists(None):
                if not self.default_profile_initialized:
                    # Read profiles fileobj and get default profile
                    defaultprofile = self.get_default_profile_path()
                    if defaultprofile is not None:
                        # Preferences monitoring
                        prefs_path = os.path.join(defaultprofile, "prefs.js")
                        logging.debug(
                            "Monitoring Firefox preferences file at %s" % prefs_path)
                        self._setup_preferences_file_monitor(prefs_path)
                        self.default_profile_initialized = True
                    else:
                        logging.debug(
                            "No default profile found at profiles file")
            else:
                logging.debug(
                    "Firefox profiles file %s is not present (yet)" % fileobj.get_path())

            # Exit mainloop if we are testing
            logging.debug(
                "test_profiles_file_updated = %s" % self.test_profiles_file_updated)
            if self.test_profiles_file_updated:
                logging.debug("Exiting mainloop after testing")
                self.test_profiles_file_updated()

    def _preferences_file_updated(self, monitor, fileobj, otherfile, eventType):
        if eventType == Gio.FileMonitorEvent.CHANGES_DONE_HINT or eventType is None:
            path = fileobj.get_path()
            logging.debug(
                "Firefox Preference file %s notifies changes done hint. %s %s %s %s" % (
                    path, monitor, fileobj, otherfile, eventType))
            if fileobj.query_exists(None):
                logging.debug(
                    "Preference file %s exists. Loading it" % path)
                # data = fileobj.load_contents(None)[1]
                with open(path, 'r') as fd:
                    data = fd.read()
                    fd.close()
                logging.debug(
                    "Preference file %s Loaded. Loading preferences." % path)
                prefs = self.load_firefox_preferences(data)
                if not path in self.monitored_preferences:
                    logging.debug(
                        "Initial preferences loaded")
                    self.monitored_preferences[path] = prefs
                else:
                    logging.debug(
                        "New preferences loaded. Checking for changes")
                    for preference in prefs.keys():
                        value = prefs[preference]
                        if preference in self.monitored_preferences[path]:
                            prev = self.monitored_preferences[path][preference]
                            logging.debug(
                                "%s - Previously: %s, now: %s" % (
                                    preference, prev, value))
                            if value != prev:
                                # Submit this config change
                                logging.debug(
                                    "Previous preference value is different. %s != %s.  Submitting change." % (
                                        value, prev))
                                self.submit_config_change(preference, value)
                        else:
                            # Submit this setting
                            logging.debug(
                                "Preference %s = %s is not present. Submitting change." % (preference, value))
                            self.submit_config_change(preference, value)

                        self.monitored_preferences[path][preference] = value
                self.default_profile_prefs_initialized = True
            else:
                logging.debug("Firefox Preferences file %s is not present (yet)" % path)
            if self.test_prefs_file_updated:
                logging.debug("Exiting mainloop after testing")
                self.test_prefs_file_updated()

    def get_default_profile_path(self):
        keyfile = GLib.KeyFile()
        try:
            if not keyfile.load_from_file(
                    self.profiles_path, GLib.KeyFileFlags.NONE):
                raise Exception('Error loading data from file')
        except Exception as e:
            logging.debug(
                "Could not open/parse %s: %s" % (self.profiles_path, e))
            return None;

        groups = keyfile.get_groups()[0];
        for group in groups:
            logging.debug("Checking profile %s" % group)
            try:
                if keyfile.get_string(group, "Default") != "1":
                    continue
            except Exception:
                continue
            return os.path.join(
                self.datadir, keyfile.get_string(group, "Path"))
        # This should never happen
        logging.debug(
            "There was no profile in %s with Default=1" % self.profiles_path)
        return None

    def load_firefox_preferences(self, data):
        pref_start = 'user_pref("'
        pref_end = ');'
        prefs = {}
        lines = data.splitlines()
        for line in lines:
            if line.startswith(pref_start) and line.endswith(pref_end):
                # Remove start and end
                linedata = line[len(pref_start) - 1:]
                linedata = linedata[:-len(pref_end)]
                # Prepare JSON data
                linedata = r'{"data": [%s]}' % linedata
                # Get key and value
                try:
                    logging.debug('Parsing preference data: %s' % linedata)
                    pref = json.loads(linedata)
                    key = pref["data"][0]
                    value = pref["data"][1]
                    prefs[key] = value
                except Exception as e:
                    logging.debug(
                        "Preference parse error. Ignoring %s (%s)" % (line, e))

        return prefs


class FleetCommanderLogger(object):
    """
    Fleet Commander Logger main class
    """

    def __init__(self, use_device_file=True):
        logging.info("Initializing Fleet Commander Logger")
        self.ml = GLib.MainLoop()
        self.homedir = GLib.get_home_dir();

        self.testing = "FC_TESTING" in os.environ

        # Initialize SPICE port manager
        if use_device_file:
            self.connmgr = SpicePortManager()
        else:
            self.connmgr = SpicePortManager('/tmp/fleet-commander-logger_spiceport')

        # Initialize screensaver inhibition
        self.scinhibitor = ScreenSaverInhibitor()

        # Initialization of logger classes
        GSettingsLogger(self.connmgr)
        NMLogger(self.connmgr)
        ChromiumLogger(self.connmgr)
        ChromeLogger(self.connmgr)
        FirefoxLogger(self.connmgr)

    def run(self):
        # Run main loop
        self.ml.run()

    def quit(self):
        # Disable screensaver inhibition after main loop exits
        self.scinhibitor.uninhibit()
        self.ml.quit()


if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action='store_true', help="Verbose output")
    parser.add_argument(
        "-n", "--no-devfile", action='store_false', help="Don't use a device file for SPICE channel")
    parser.add_argument(
        "-v", "--verbose", action='store_true', help="Verbose output")
    args = parser.parse_args()

    if args.debug or args.verbose:
        log = logging.getLogger()
        level = logging.getLevelName('DEBUG')
        log.setLevel(level)

    fcl = FleetCommanderLogger(use_device_file=args.no_devfile)
    fcl.run()
