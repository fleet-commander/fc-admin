#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

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

# Python imports
import sqlite3
import json

SCHEMA_VERSION = 1.0


class SQLiteDict(object):
    """
    Configuration values database handler
    """

    _SUPPORTED_TYPES = {
        'int':     int,
        'long':    long,
        'float':   float,
        'str':     str,
        'unicode': unicode,
        'tuple':   tuple,
        'list':    list,
        'dict':    dict,

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
            'key':    unicode,
            'value':  unicode,
            'type':   unicode,
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
        if valuetype not in self._SUPPORTED_TYPES.keys():
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


class ConfigValues(SQLiteDict):
    """
    Configuration values database handler
    """
    TABLE_NAME = 'config'


class SessionSettings(object):

    TABLE_NAME = 'sessionsettings'

    def __init__(self, db):
        """
        Class initialization
        """
        self.db = db
        self.cursor = db.cursor
        # Generate table if not exists
        self.db.create_table(self.TABLE_NAME, **{
            'collector': unicode,
            'key':       unicode,
            'value':     unicode,
            'selected':  int,
        })

    def update_setting(self, collectorname, key, value):
        """
        Updates a setting in database or creates it if it does not exist
        """
        # Try to update any existing row
        updatequery = 'UPDATE %s SET value=? WHERE collector=? and key=?'
        self.cursor.execute(updatequery % self.TABLE_NAME, (value, collectorname, key))

        # Make sure it exists
        insertquery = 'INSERT OR IGNORE INTO %s (collector, key, value, selected) VALUES (?,?,?,?)'
        self.cursor.execute(insertquery % self.TABLE_NAME, (collectorname, key, value, 0))

        # Commit changes
        self.db.conn.commit()

    def get_setting(self, collectorname, key):
        """
        Updates a setting in database or creates it if it does not exist
        """
        # Try to update any existing row
        query = 'SELECT value FROM %s WHERE collector=? AND key=?'
        self.cursor.execute(query % self.TABLE_NAME, (collectorname, key))
        data = self.cursor.fetchone()
        if data is not None:
            return data[0]
        raise KeyError('There is no setting with key %s for collector name %s' % (key, collectorname))

    def get_for_collector(self, collectorname, only_selected=False):
        """
        Returns settings for a given collector and filtered by selected only if specified
        """
        query = 'SELECT key, value FROM %s WHERE collector=?'
        if only_selected:
            query += ' AND selected=1'
        result = self.cursor.execute(query % self.TABLE_NAME, (collectorname,))
        return {k: v for k, v in result}

    def select_settings(self, collectorname, keys):
        """
        Marks given keys for a collector as selected
        """
        query = 'UPDATE %s SET selected=1 WHERE key IN (%s)' % (self.TABLE_NAME, ','.join('?'*len(keys)))
        self.cursor.execute(query, keys)
        self.db.conn.commit()

    def clear_settings(self, collectorname=None):
        """
        Clear settings for a given collector or all collectors at once
        """
        query = 'DELETE FROM %s'
        if collectorname is not None:
            query += 'WHERE collector=?'
            self.cursor.execute(query % self.TABLE_NAME, collectorname)
        else:
            self.cursor.execute(query % self.TABLE_NAME)
        self.db.conn.commit()


class DBManager(object):
    """
    Database manager class
    """

    SQLITE_TYPE_MATCHES = {
        None:    'NULL',
        int:     'INTEGER',
        long:    'INTEGER',
        float:   'REAL',
        str:     'TEXT',
        unicode: 'TEXT',
        buffer:  'BLOB'
    }

    def __init__(self, database):
        """
        Class initialization
        """
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()
        # Initialize configuration data
        self.config = ConfigValues(self)
        # Session settings initialization
        self.sessionsettings = SessionSettings(self)

    def create_table(self, name, **structure):
        """
        Creates a table
        """
        col_types = ['%s %s' % (colname, self.SQLITE_TYPE_MATCHES[coltype]) for colname, coltype in structure.items()]
        query = "CREATE TABLE IF NOT EXISTS %s (%s)" % (name, ','.join(col_types))
        self.cursor.execute(query)
        self.conn.commit()
