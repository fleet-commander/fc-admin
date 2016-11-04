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

function BaseCollector(namespace) {
    this.namespace = namespace;
    this.changes = {};
    this.key_name = 'key';
};

BaseCollector.prototype = {

  get_key_from_change: function(change) {
    if (this.key_name in change) return change[this.key_name];
    return undefined;
  },

  get_value_from_change: function(change) {
    if ('value' in change) return change.value;
    return undefined;
  },

  handle_change: function(change) {
    DEBUG > 0 && console.log(
      'FC: Collector', this.namespace, 'handling change', change);
    var key = this.get_key_from_change(change)
    if (key != undefined) {
      this.changes[key] = change
    } else {
      DEBUG > 0 && console.log(
        'FC: Collector', this.namespace, 'can not handle change', change);
    }
  },

  dump_changes: function() {
    var self = this;
    var changelist = [];
    $.each(this.changes, function(k, v){
      changelist.push([k, self.get_value_from_change(v)]);
    });
    return changelist;
  },

  get_changeset: function(selected_keys) {
    var self = this;
    var changeset = [];
    $.each(selected_keys, function(i, key){
      if (key in self.changes) changeset.push(self.changes[key]);
    });
    return changeset;
  }
}


function NMCollector(namespace) {
  BaseCollector.apply(this, arguments);
  this. key_name = 'uuid';
};

NMCollector.prototype = Object.create(BaseCollector.prototype);

NMCollector.prototype.get_value_from_change = function(change) {
  if ('type' in change && 'id' in change) {
    return change.type + ' - ' + change.id;
  }
  return undefined;
}
