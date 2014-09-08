#!/usr/bin/python3

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

import logging

from argparse import ArgumentParser
from gi.repository import GLib, Gio, Json
from http.client import HTTPConnection

logger = logging.getLogger(__name__)

DEFAULT_HTTP_SERVER = 'localhost:8181'

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
    no longer satisfy the (expanded) changed key set.  When only on candidate
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

        headers = {'Content-type': 'application/json'}
        self.connection.request('POST', '/submit_change', data, headers)
        response = self.connection.getresponse()

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

if __name__ == '__main__':

    parser = ArgumentParser(description='Log session changes')
    parser.add_argument(
        '--debug', action='store_const', dest='loglevel',
        const=logging.DEBUG, default=logging.WARNING,
        help='print debugging information')
    parser.add_argument(
        '--server', action='store', metavar='HOST[:PORT]',
        default=DEFAULT_HTTP_SERVER,
        help='HTTP server address (default: %s)' % DEFAULT_HTTP_SERVER)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    connection = HTTPConnection(args.server)

    gsettings_logger = GSettingsLogger(connection)

    GLib.MainLoop().run()

