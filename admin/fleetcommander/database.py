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
import sqlite3
import json
import six

SCHEMA_VERSION = 1.0


class SQLiteDict(object):
    """
    Configuration values database handler
    """

    _SUPPORTED_TYPES = {
        'int':     int,
        'long':    int if six.PY3 else long,
        'float':   float,
        'str':     str,
        'unicode': six.text_type,
        'tuple':   tuple,
        'list':    list,
        'dict':    dict,
        'bytes':   bytes,
    }

    _SERIALIZED_TYPES = ['tuple', 'list', 'dict']

    TABLE_NAME = 'sqlitedict_table'

    def __init__(self, db):
        """
        Class initialization
        """
        self.db = db
        self.cursor = db.cursor
        # Generate table if not exists
        self.db.create_table(self.TABLE_NAME, **{
            'key':    six.text_type,
            'value':  six.text_type,
            'type':   six.text_type,
        })

        if 'SCHEMA_VERSION' not in self:
            self['SCHEMA_VERSION'] = SCHEMA_VERSION
        else:
            # Check schema version
            schema_version = self['SCHEMA_VERSION']
            if schema_version != SCHEMA_VERSION:
                if schema_version < SCHEMA_VERSION:
                    # TODO: Update schema
                    pass
                else:
                    # TODO: Raise an error?
                    pass

    def __getitem__(self, key):
        """
        Evaluation of config[key]
        """
        self.cursor.execute('SELECT value, type FROM %s WHERE key = ?' % self.TABLE_NAME, (key,))
        data = self.cursor.fetchone()
        if data is not None:
            valuetype = self._SUPPORTED_TYPES[data[1]]
            if data[1] in self._SERIALIZED_TYPES:
                value = json.loads(data[0])
            else:
                value = data[0]
            return valuetype(value)
        raise KeyError(key)

    def __setitem__(self, key, value):
        """
        Assignement to config[key]
        """
        if key in self:
            self.__delitem__(key)

        valuetype = type(value).__name__
        if valuetype not in list(self._SUPPORTED_TYPES.keys()):
            raise ValueError('Type %s is not supported by SQLiteDict' % valuetype)

        if valuetype in self._SERIALIZED_TYPES:
            value = json.dumps(value)

        self.cursor.execute('INSERT INTO %s (key, value, type) values (?, ?, ?)' % self.TABLE_NAME, (key, value, valuetype))
        self.db.conn.commit()

    def __delitem__(self, key):
        """
        Item deletion
        """
        self.cursor.execute('DELETE FROM %s WHERE key=?' % self.TABLE_NAME, (key,))
        self.db.conn.commit()

    def __contains__(self, key):
        """
        Item membership by key
        """
        self.cursor.execute('SELECT value FROM %s WHERE key=?' % self.TABLE_NAME, (key,))
        data = self.cursor.fetchone()
        return data is not None

    def get(self, key, default=None):
        """
        Return key value or default value if key does not exists
        """
        try:
            return self[key]
        except:
            return default

    def setdefault(self, key, value):
        """
        Set default value for a given key if it does not exist already
        """
        if key not in self:
            self[key] = value
        return self[key]

    def items(self):
        """
        Return list of tuples with current items
        """
        self.cursor.execute(
            'SELECT key, value, type FROM %s' % self.TABLE_NAME)
        for row in self.cursor.fetchall():
            if row[0] != 'SCHEMA_VERSION':
                valuetype = self._SUPPORTED_TYPES[row[2]]
                if row[2] in self._SERIALIZED_TYPES:
                    value = json.loads(row[1])
                else:
                    value = row[1]
                yield (row[0], valuetype(value))


class ConfigValues(SQLiteDict):
    """
    Configuration values database handler
    """
    TABLE_NAME = 'config'


class ProfilesData(SQLiteDict):
    """
    Configuration values database handler
    """
    TABLE_NAME = 'profiles'


class BaseDBManager(object):
    """
    Database manager class
    """

    SQLITE_TYPE_MATCHES = {
        None:    'NULL',
        int:     'INTEGER',
        float:   'REAL',
        str:     'TEXT',
        six.text_type: 'TEXT',
        memoryview:  'BLOB'
    }
    if six.PY3:
        SQLITE_TYPE_MATCHES[bytes] = 'BLOB'
    else:
        SQLITE_TYPE_MATCHES[buffer] = 'BLOB'
        SQLITE_TYPE_MATCHES[long] = 'INTEGER'

    def __init__(self, database):
        """
        Class initialization
        """
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()

    def create_table(self, name, **structure):
        """
        Creates a table
        """
        col_types = ['%s %s' % (colname, self.SQLITE_TYPE_MATCHES[coltype]) for colname, coltype in structure.items()]
        query = "CREATE TABLE IF NOT EXISTS %s (%s)" % (name, ','.join(col_types))
        self.cursor.execute(query)
        self.conn.commit()


class DBManager(BaseDBManager):
    """
    Database manager class
    """

    def __init__(self, database):
        """
        Class initialization
        """
        super(DBManager, self).__init__(database)
        # Initialize configuration data
        self.config = ConfigValues(self)
        # Profiles
        self.profiles = ProfilesData(self)
