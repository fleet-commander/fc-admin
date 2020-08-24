/*
* Copyright (C) 2014 Red Hat, Inc.
*
* This program is free software; you can redistribute it and/or
* modify it under the terms of the GNU Lesser General Public
* License as published by the Free Software Foundation; either
* version 2.1 of the licence, or (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
* Lesser General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public
* License along with this program; if not, see <http://www.gnu.org/licenses/>.
*
* Author: Oliver Gutiérrez <ogutierrez@redhat.com>
*/

/*global $ */
/*global DEBUG */

"use strict";

function BaseCollector(namespace) {
    this.namespace = namespace;
    this.changes = {};
    this.key_name = 'key';
}

BaseCollector.prototype = {

    get_key_from_change: function (change) {
        if (change[this.key_name] !== undefined) {
            return change[this.key_name];
        }
        return undefined;
    },

    get_value_from_change: function (change) {
        if (change.value !== undefined) {
            return change.value;
        }
        return undefined;
    },

    handle_change: function (change) {
        if (DEBUG > 0) {
            console.log(
                'FC: Collector',
                this.namespace,
                'handling change',
                change
            );
        }
        var key = this.get_key_from_change(change);
        if (key !== undefined) {
            this.changes[key] = change;
        } else {
            if (DEBUG > 0) {
                console.log(
                    'FC: Collector',
                    this.namespace,
                    'can not handle change',
                    change
                );
            }
        }
    },

    dump_changes: function () {
        var self = this, changelist = [];
        $.each(this.changes, function (k, v) {
            changelist.push([k, self.get_value_from_change(v)]);
        });
        return changelist;
    },

    get_changeset: function (selected_keys) {
        var self = this, changeset = [];
        /*jslint unparam: true */
        $.each(selected_keys, function (ignore, key) {
            if (self.changes[key] !== undefined) {
                changeset.push(self.changes[key]);
            }
        });
        /*jslint unparam: false */
        return changeset;
    }
};

// Network Manager specific collector
function NMCollector(namespace) {
    BaseCollector.apply(this, namespace);
    this.key_name = 'uuid';
}

NMCollector.prototype = Object.create(BaseCollector.prototype);

NMCollector.prototype.get_value_from_change = function (change) {
    if (change.type !== undefined && change.id !== undefined) {
        return change.type + ' - ' + change.id;
    }
    return undefined;
};

// Firefox bookmarks specific collector
function FirefoxBookmarksCollector(namespace) {
    BaseCollector.apply(this, namespace);
}

FirefoxBookmarksCollector.prototype = Object.create(BaseCollector.prototype);

FirefoxBookmarksCollector.prototype.get_value_from_change = function (change) {
    return change.value.URL + ' - ' + change.value.Title;
};
