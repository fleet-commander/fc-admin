#!/usr/bin/python3
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
#          Matthew Barnes <mbarnes@redhat.com>

# XXX May want to eventually break this into one logger class per
#     file so it's more manageable, but we're not quite there yet.

import json
import logging
import os.path
import sys
import configparser


from argparse import ArgumentParser

from gi.repository import GLib, Gio, Json
from http.client import HTTPConnection

logger = logging.getLogger(__name__)

DEFAULT_HTTP_HOST = 'localhost'
DEFAULT_HTTP_PORT = '8181'
CHANGE_SUBMIT_PATH = '/submit_change/'

class ScreenSaverInhibitor(object):
    def __init__(self, inhibit=False):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
                                            'org.freedesktop.ScreenSaver', '/ScreenSaver',
                                            'org.freedesktop.ScreenSaver', None)
        self.cookie = None

        if inhibit:
            self.inhibit()

    def inhibit(self):
        if self.cookie != None:
            return

        self.cookie = self.proxy.Inhibit('(ss)', 'org.gnome.FleetCommander.Logger',
                                         'Preventing ScreenSaver from showing up while Fleet Commander gathers configuration changes')
    def uninhibit(self):
        if self.cookie == None:
            return

        self.proxy.UnInhibit('(u)', self.cookie)
        self.cookie = None

class ConnectionManager(object):
    '''Manages HTTP connections so that Loggers don't have to
       it also queues commands in case the HTTP server goes away.'''
    headers = {'Content-type': 'application/json'}
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.queue = []
        self.source = None

    def submit_change(self, namespace, data):
        try:
            conn = HTTPConnection("%s:%s" % (self.host, self.port))
            conn.request('POST', CHANGE_SUBMIT_PATH+namespace, data, self.headers)
            resp = conn.getresponse()
            #TODO: collect response code
        except:
            self._log_web_error()
            if self.source == None:
                self.source = GLib.timeout_add(5000, self.timeout)
            self.queue.append((namespace, data))

    def timeout(self):
        try:
            conn = HTTPConnection("%s:%s" % (self.host, self.port))
            while self.queue:
                ns, data = self.queue[0]
                conn.request('POST', CHANGE_SUBMIT_PATH+ns, data, self.headers)
                conn.getresponse()
                #TODO: collect response code
                self.queue.pop(0)
        except:
            #Try again later
            self._log_web_error()
            return True

        self.source = None
        return False

    def _log_web_error(self):
         logger.error("Could not connect to web service %s:%s" % (self.host, self.port))

class GoaLogger(object):
    '''Logs changes to GNOME Online Accounts.

    This is a simple logger class that monitors the "accounts.conf" key
    file for updates from the GNOME Online Accounts daemon (goa-daemon).

    When an update occurs, this class parses and filters the file contents,
    converts the key file syntax to a JSON object (group names become member
    names, with a few tweaks), and submits the update to the HTTP server.'''

    def __init__(self, connection):
        self.connection = connection

        user_config_dir = GLib.get_user_config_dir()
        self.path = os.path.join(user_config_dir, 'goa-1.0', 'accounts.conf')

        # Abbreviated path for debug messages.
        self.debug_path = os.path.relpath(self.path, user_config_dir)

        self.monitor = Gio.File.new_for_path(self.path). \
                       monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect('changed', self.__file_changed_cb)

        if os.path.exists(self.path):
            self.update()

    def __file_changed_cb(self, monitor, this_file, other_file, event_type):
        logger.debug(
            'GFileMonitor::changed("%s", %s)',
            self.debug_path, event_type.value_nick)

        if event_type in (Gio.FileMonitorEvent.CHANGED,
                          Gio.FileMonitorEvent.CREATED,
                          Gio.FileMonitorEvent.DELETED):
            self.update()

    def update(self):
        config = configparser.ConfigParser()

        # Preserve "CamelCase" in option names.
        config.optionxform = str

        # For DELETED events, this just skips the deleted file
        # resulting in an empty dataset, which is what we want.
        config.read(self.path)

        # Filter out temporary accounts (e.g. kerberos) and user-controlled
        # options (CalendarEnabled, ContactsEnabled, DocumentsEnabled, etc).
        for section in config.sections():
            if config[section].getboolean('istemporary'):
                del config[section]
            else:
                for option in config[section]:
                    if option.endswith('enabled'):
                        del config[section][option]

        # Modify the remaining account IDs so they don't conflict with
        # user-created accounts on client machines.
        for section in config.sections():
            # Section name is 'Account account_TIMESTAMP_COUNT'.
            # Replace it with 'fcmdr_account_TIMESTAMP_COUNT'.
            new_section = 'fcmdr_' + section.split()[-1]
            config.add_section(new_section)
            new_section_proxy = config[new_section]
            for k, v in config.items(section):
                new_section_proxy[k] = v
            del config[section]

        # Substitute occurrences of the account user name and real name
        # with ${username} and ${realname} variables.  The user name is
        # derived from particular account options.
        for section in config.sections():
            section_proxy = config[section]

            if 'name' in section_proxy:
                section_proxy['name'] = '${realname}'

            username = section_proxy.get('identity')
            if username:
                if '@' in username:
                    username = username.split('@')[0]
                for key, value in section_proxy.items():
                    new_value = value.replace(username, '${username}')
                    section_proxy[key] = new_value

        # Convert to JSON format.
        data = json.dumps({s: dict(config.items(s)) for s in config.sections()})

        self.connection.submit_change('org.gnome.online-accounts', data)

class GSettingsLogger(object):
    '''Logs all GSettings changes.

    This class monitors the ca.desrt.dconf.Writer interface directly for
    "Notify" signals.  This allows it to capture change notifications for
    both fixed path AND relocatable GSettings schemas.

    Logging changes for fixed-path schemas is trivial, because the path is
    encoded into the schema itself.  So given the changed path, it's just a
    reverse-lookup to find the fixed-path schema.

    Logging changes for relocatable schemas is more complex because it
    involves guessing.  It uses a process of elimination to determine which
    relocatable schema is in use at a particular path.

    There's a fixed set of relocatable schemas, each of which defines a set
    of keys.  As we receive change notifications for a path which we know is
    using a relocatable schema, we accumulate a set of changed key names for
    that path which serve as clues.

    On the first notification for such a path, we evaluate ALL relocatable
    schemas and select candidates which satisfy the initial changed key set.
    This can yield an ambiguous result if multiple relocatable schemas define
    the key(s) we know have changed.  Only one of the candidate schemas is
    the correct one, but regardless we create a Settings object for each
    candidate schema at the same path.  (It turns out GLib doesn't care; its
    enforcement of relocatable schemas is surprisingly weak.)

    This CAN yield bogus change entries in the log (right key, wrong schema).

    As the changed key set for that path expands from further notifications,
    we reexamine the candidate schemas for that path and eliminate those that
    no longer satisfy the (expanded) changed key set.  When only one candidate
    remains, we can conclude with certainty which relocatable schema is in use
    at that path.
    '''

    BUS_NAME = 'ca.desrt.dconf'
    OBJECT_PATH = '/ca/desrt/dconf/Writer/user'
    INTERFACE_NAME = 'ca.desrt.dconf.Writer'

    def __init__(self, connection):
        self.connection = connection

        # path_to_known_settings : { 'path': Settings }
        #
        # This is for Settings objects with fixed-path schemas
        # and also relocatable schemas which we're certain of.
        self.path_to_known_settings = {}

        # path_to_reloc_settings : { 'path' : { SettingsSchema : Settings } }
        #
        # This is for Settings objects with relocatable schemas which we're
        # uncertain of.  The goal is to narrow the candidate set for a
        # particular path to one and then move that last Settings object to
        # self.path_to_known_settings.
        self.path_to_reloc_settings = {}

        # path_to_changed_keys : { 'path' : { 'key', ... } }
        #
        # The set of keys we've observed changes to, by path.
        self.path_to_changed_keys = {}

        # relocatable_schemas : [ SettingsSchema, ... ]
        self.relocatable_schemas = []

        self.dconf_subscription_id = 0

        schema_source = Gio.SettingsSchemaSource.get_default()

        # Populate a table of paths to Settings objects.  We can do this up
        # front for fixed-path schemas.  For relocatable schemas we have to
        # wait for a change to occur and then try to derive the schema from
        # the path and key(s) in the change notification.
        for schema_name in Gio.Settings.list_schemas():
            schema = schema_source.lookup(schema_name, True)
            path = schema.get_path()
            settings = self.__new_settings_for_schema(schema, path)
            self.path_to_known_settings[path] = settings

        for schema_name in Gio.Settings.list_relocatable_schemas():
            schema = schema_source.lookup(schema_name, True)
            self.relocatable_schemas.append(schema)

        # Listen directly to dconf's D-Bus interface so we're notified of
        # changes on ALL paths, regardless of schema.
        Gio.bus_watch_name(
            Gio.BusType.SESSION,
            self.BUS_NAME,
            Gio.BusNameWatcherFlags.NONE,
            self.__dconf_bus_name_appared_cb,
            self.__dconf_bus_name_vanished_cb)

    def __settings_changed_cb(self, settings, key):
        logger.debug(
            'GSettings::changed("%s", "%s") at %s',
             settings.props.schema_id, key, settings.props.path)

        assert settings.props.path.endswith('/')

        variant = settings.get_value(key)

        # XXX We could use Python's built-in json module if it weren't for
        #     the fact that we have to serialize a GLib.Variant object and
        #     building a JSON object from two different JSON APIs seems...
        #     problematic.  The json-glib Python bindings are rather more
        #     cumbersome, but they'll do.

        json_object = Json.Object.new()
        json_object.set_string_member('key', settings.props.path + key)
        json_object.set_string_member('schema', settings.props.schema_id)
        json_object.set_member('value', Json.gvariant_serialize(variant))

        root = Json.Node.new(Json.NodeType.OBJECT)
        root.init_object(json_object)

        generator = Json.Generator.new()
        generator.set_root(root)
        data, length = generator.to_data()

        self.connection.submit_change('org.gnome.gsettings', data)

    def __new_settings_for_schema(self, schema, path):
        settings = Gio.Settings.new_full(schema, None, path)
        settings.connect('changed', self.__settings_changed_cb)
        return settings

    def __path_to_reloc_settings_add(self, path, keys):
        def has_all_keys(schema):
            return all([schema.has_key(k) for k in keys])

        candidate_schemas = filter(has_all_keys, self.relocatable_schemas)

        # Avoid leaving an empty dictionary in self.path_to_reloc_settings
        # so path lookups work as expected.
        if not candidate_schemas:
            logger.debug('>>> No candidate schemas!')
            return 0

        reloc_settings = self.path_to_reloc_settings.setdefault(path, {})
        for schema in candidate_schemas:
             if schema not in reloc_settings:
                 # XXX We create the Settings object early enough to
                 #     pick up and log the dconf change notification
                 #     we're handling.  At least I think.  Test this
                 #     more thoroughly to be sure.
                 logger.debug(
                     '>>> Adding candidate schema "%s"', schema.get_id())
                 settings = self.__new_settings_for_schema(schema, path)
                 reloc_settings[schema] = settings

        return len(reloc_settings)

    def __path_to_reloc_settings_audit(self, path, keys):
        def has_all_keys(schema):
            return all([schema.has_key(k) for k in keys])

        if path not in self.path_to_reloc_settings:
            return 0

        # Remove any Settings objects with schemas that are in conflict
        # with our key change observations from dconf.  The hope is to
        # observe enough key changes on a particular path that we can
        # discover through elimination which relocatable schema is in
        # use at that path.

        reloc_settings = self.path_to_reloc_settings[path]
        # Convert the keys() iterator to a list since we're deleting items.
        for schema in list(reloc_settings.keys()):
            if not has_all_keys(schema):
                logger.debug(
                    '>>> Removing candidate schema "%s"', schema.get_id())
                del reloc_settings[schema]

        n_schemas = len(reloc_settings)

        # Avoid leaving an empty dictionary in self.path_to_reloc_settings
        # so path lookups work as expected.
        if not reloc_settings:
            del self.path_to_reloc_settings[path]

        return n_schemas

    def __dconf_writer_notify_cb(self, connection, sender_name, object_path,
                                 interface_name, signal_name, parameters,
                                 user_data):
        # 'keys' is only relevant if 'path' has a trailing slash.
        # Otherwise 'path' is actually path/key is 'keys' is empty.
        path, keys, tag = parameters
        if not path.endswith('/'):
            path, key = path.rsplit('/', 1)
            path = path + '/'
            keys = [key]

        logger.debug(
            'dconf Notify: %s (%s)', path,
            'schema known' if path in self.path_to_known_settings
            else 'schema not yet known')

        logger.debug('>>> Keys: ' + str(', ').join(keys))

        # Do nothing if we already know the schema at this path.
        # Our Settings::changed callback will record the change.
        if path in self.path_to_known_settings:
            return

        # Note the keys that changed on this path.  We know a relocatable
        # schema is in use at this path, but we can't be certain which one.
        # However the probability of guessing right increases as the number
        # of changed keys on this path accumulates, because we can compare
        # the accumulated set of changed keys to the schemas' keys.
        changed_keys = self.path_to_changed_keys.setdefault(path, set())
        for key in keys:
            changed_keys.add(key)

        if path in self.path_to_reloc_settings:
            n_schemas = self.__path_to_reloc_settings_audit(path, changed_keys)
        else:
            n_schemas = self.__path_to_reloc_settings_add(path, changed_keys)

        if n_schemas == 1:
            reloc_settings = self.path_to_reloc_settings.pop(path)
            assert len(reloc_settings) == 1
            schema, settings = reloc_settings.popitem()
            logger.debug (
                '>>> Electing candidate schema "%s"', schema.get_id())
            self.path_to_known_settings[path] = settings

    def __dconf_bus_name_appared_cb(self, connection, name, owner):
        self.dconf_subscription_id = connection.signal_subscribe(
            owner,
            self.INTERFACE_NAME,
            'Notify',
            self.OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self.__dconf_writer_notify_cb,
            None)

    def __dconf_bus_name_vanished_cb(self, connection, bus_name):
        if self.dconf_subscription_id:
            connection.signal_unsubscribe(self.dconf_subscription_id)
            self.dconf_subscription_id = 0

def parse_config(config_file):
    arg = {'host': None, 'port': None}
    config = configparser.ConfigParser()

    try:
        config.read(config_file)
        config["logger"]
    except FileNotFoundError:
        logging.error('Could not find configuration file %s' % config_file)
        sys.exit(1)
    except configparser.ParsingError:
        logging.error('There was an error parsing %s' % config_file)
        sys.exit(1)
    except KeyError:
        logging.error('Configuration file %s has no "logger" section' % config_file)
        sys.exit(1)
    except:
        logging.error('There was an unknown error parsing %s' % config_file)
        sys.exit(1)

    arg['host'] = config['logger'].get('admin_server_host')
    arg['port'] = config['logger'].get('admin_server_port')
    return arg

if __name__ == '__main__':
    parser = ArgumentParser(description='Log session changes')
    parser.add_argument(
        '--debug', action='store_const', dest='loglevel',
        const=logging.DEBUG, default=logging.WARNING,
        help='print debugging information')
    parser.add_argument(
        '--host', action='store', metavar='HOST', default=DEFAULT_HTTP_HOST,
        help='HTTP server host (default: %s)' % DEFAULT_HTTP_HOST)
    parser.add_argument(
        '--port', action='store', metavar='HOST', default=DEFAULT_HTTP_PORT,
        help='HTTP server port (default: %s)' % DEFAULT_HTTP_PORT)
    parser.add_argument(
        '--configuration', action='store', metavar='CONFIGFILE', default=None,
        help='Provide a configuration file path for the logger (overrides --port and --host)')

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    if args.configuration:
      conf = parse_config(args.configuration)
      if conf['host']:
        args.host = conf['host']
      if conf['port']:
        args.port = conf['port']

    connection = ConnectionManager(args.host, args.port)
    gsettings_logger = GSettingsLogger(connection)
    goa_logger = GoaLogger(connection)
    inhibitor = ScreenSaverInhibitor(True)

    GLib.MainLoop().run()
