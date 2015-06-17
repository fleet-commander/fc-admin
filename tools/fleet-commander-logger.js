#!/usr/bin/gjs
/*
 * Copyright (c) 2015 Red Hat, Inc.
 *
 * GNOME Maps is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * GNOME Maps is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with GNOME Maps; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Authors: Alberto Ruiz <aruiz@redhat.com>
 *          Matthew Barnes <mbarnes@redhat.com>
 */


const GLib = imports.gi.GLib;
const Gio  = imports.gi.Gio;
const Soup = imports.gi.Soup;
const Json = imports.gi.Json;

//Global constants
const RETRY_INTERVAL = 1000;
const SUBMIT_PATH    = '/submit_change/';

//Mainloop
const ml = imports.mainloop;

//Global application objects
var inhibitor       = null;

//Global settings
var options = null;
var _debug = false;

function debug (msg) {
  if (!_debug)
      return;
  printerr("DEBUG: " + msg);
}

function hasSuffix (haystack, needle) {
    return (haystack.length - needle.length) == haystack.lastIndexOf(needle);
}

function parse_options () {
  let result = {
      'admin_server_host': 'localhost',
      'admin_server_port': 8181
  }

  let file = null;

  for(let i = 0; i < ARGV.length; i++) {
    switch(ARGV[i]) {
      case "--help":
      case "-h":
        printerr("--help/-h:               show this output message");
        printerr("--configuration/-c FILE: sets the configuration file");
        printerr("--debug/-d/-v:           enables debugging/verbose output");
        break;
      case "--debug":
      case "-d":
      case "-v":
        _debug = true;
        debug("Debugging output enabled");
        break;
      case "--configuration":
        i++;
        if (ARGV.length == i) {
          printerr("ERROR: No configuration value was provided");
          return null;
        }

        debug(ARGV[i] + " selected as configuration file");

        if (!GLib.file_test (ARGV[i], GLib.FileTest.EXISTS)) {
            printerr("ERROR: " + ARGV[i] + " does not exists");
            return null;
        }
        if (!GLib.file_test (ARGV[i], GLib.FileTest.IS_REGULAR)) {
            printerr("ERROR: " + ARGV[i] + " is not a regular file");
            return null;
        }

        let kf = new GLib.KeyFile();
        try {
            kf.load_from_file(ARGV[i], GLib.KeyFileFlags.NONE);
        } catch (e) {
            debug(e);
            printerr("ERROR: Could not parse configuration file " + ARGV[i]);
            return null;
        }

        if (!kf.has_group("logger")) {
            printerr("ERROR: "+ARGV[i]+" does not have [logger] section");
            return null;
        }
        try {
            result['admin_server_host'] = kf.get_value("logger", "admin_server_host");
        } catch (e) {
            debug (e);
        }
        try {
            result['admin_server_port'] = kf.get_value("logger", "admin_server_port");
        } catch (e) {
            debug (e);
        }
        break;
    }
  }

  debug ("admin_server_host: " + result['admin_server_host'] + " - admin_server_port: " + result['admin_server_port']);
  return result;
}


var ScreenSaverInhibitor = function () {
    let bus = Gio.bus_get_sync(Gio.BusType.SESSION, null);
    this.proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, null,
                                        'org.freedesktop.ScreenSaver', '/ScreenSaver',
                                        'org.freedesktop.ScreenSaver', null);
    this.cookie = null;

    this.inhibit();
}

ScreenSaverInhibitor.prototype.inhibit = function () {
    debug("Inhibiting screen saver");
    if (this.cookie != null) {
        debug("Screen saver already inhibited");
        return;
    }

    try {
        let args =  new GLib.Variant('(ss)', 'org.gnome.FleetCommander.Logger',
                                     'Preventing ScreenSaver from locking the screen while Fleet Commander Logger runs');
        let ret = this.proxy.call_sync('Inhibit', args, Gio.DBusCallFlags.NONE, 1000, null);
        this.cookie = ret.get_child_value(0).get_uint32();
    } catch (e) {
        debug(e);
        printerr("ERROR: There was an error attempting to inhibit the screen saver")
    }
}

ScreenSaverInhibitor.prototype.uninhibit = function () {
    debug("Uninhibiting screen saver");
    try {
        let args =  GLib.Variant.new_tuple([new GLib.Variant('u', this.cookie)], 1);
        this.proxy.call_sync('UnInhibit', args, Gio.DBusCallFlags.NONE, 1000, null);
    } catch (e) {
        debug(e);
        printerr("ERROR: There was an error attempting to uninhibit the screen saver")
    }
    this.cookie = null;
}

// ConnectionManager - This class manages the HTTP connection to the admin server
var ConnectionManager = function (host, port) {
    this.uri = new Soup.URI("http://" + host + ":" + port);
    this.session = new Soup.Session();
    this.queue = [];
    this.timeout = 0;
}
ConnectionManager.prototype._perform_submits = function () {
    if (this.queue.length < 1)
        return false;

    for (let i = 0; i < this.queue.length ; i++) {
        debug("Submitting change " + this.queue[i].ns + ":")
        debug(this.queue[i].data);

        let payload = this.queue[i].data;
        let ns      = this.queue[i].ns;

        this.uri.set_path(SUBMIT_PATH+ns);
        let msg = Soup.Message.new_from_uri("POST", this.uri);
        msg.set_request('application/json', Soup.MemoryUse.COPY, payload, payload.length);

        this.session.queue_message(msg, function (s, m) {
            debug("Response from server: returned code " + m.status_code);
            switch (m.status_code) {
                case 200:
                    debug ("Change submitted " + ns + " " + payload);
                    break;
                case 403:
                    printerr("ERROR: invalid change namespace " + ns);
                    printerr(m.response_body.data);
                    break;
                default:
                    printerr("ERROR: There was an error trying to contact the server");
                    return;
            }

            //Remove this item, if the queue is empty remove timeout
            this.queue = this.queue.splice(i, 1);
            if (this.queue.length < 1 && this.timeout > 0) {
                GLib.source_remove(this.timeout);
                this.timeout = 0;
            }
        }.bind(this));
    }
    return true;
}

ConnectionManager.prototype.submit_change = function (namespace, data) {
    debug ("Submitting changeset as namespace " + namespace)
    debug (">>> " + data);

    //FIXME: Bound the amount of queued changes
    this.queue.push({ns: namespace, data: data});


    if (this.queue.length > 0 && this.timeout < 1)
        this.timeout = GLib.timeout_add (GLib.PRIORITY_DEFAULT,
                                         RETRY_INTERVAL,
                                         this._perform_submits.bind(this));
}

var GoaLogger = function (connmgr) {
    debug("Constructing GoaLogger");
    this.connmgr = connmgr;
    this.path = [GLib.get_user_config_dir(), 'goa-1.0', 'accounts.conf'].join('/');

    this.monitor = Gio.File.new_for_path(this.path).monitor_file(Gio.FileMonitorFlags.NONE, null);

    if (GLib.file_test (this.path, GLib.FileTest.EXISTS))
        this.update();

    this.monitor.connect ('changed', function (monitor, this_file, other_file, event_type) {
        debug("GFileMonitor::changed " + [this.path, event_type.value_nick].join(" "));

        switch (event_type) {
            case Gio.FileMonitorEvent.CHANGED:
            case Gio.FileMonitorEvent.CREATED:
            case Gio.FileMonitorEvent.DELETED:
                this.update();
                break;
            default:
                break;
        }
    }.bind(this));
}

GoaLogger.prototype.update = function () {
    debug("Updating GOA configuration data");

    let kf = new GLib.KeyFile();
    try {
        kf.load_from_file(this.path, GLib.KeyFileFlags.NONE);
    } catch (e) {
        debug(e);
        printerr("ERROR: Could not parse configuration file " + this.path);
        return;
    }

    //FIXME: Send empty dataset on file removal

    //TODO: Test this and consider whether the *Enabled keys are worth ignoring
    /*kf.get_groups().forEach (function(group) {
        kf.get_keys(group).every (function (key) {
            if (key == 'IsTemporary' && kf.get_boolean(group, key)) {
                debug ("Removing group " + group + " as it is temporary");
                kf.remove_group(group);
                return false;
            }

            if (hasSuffix(key, "Enabled"))
                kf.remove_key(group, key);

            return true;
        });
    });*/

    //TODO: figure out how reliable this parametrization method is
    /* if (key == 'Identity') {
                val = ['${username}', val.split('@').pop()].join("@");
            }
     */

    let result = {};
    kf.get_groups()[0].forEach(function(group) {
        let fcmdr_group = "fcmdr_" + group.split(" ").pop();
        let fcmdr_obj = {};
        result[fcmdr_group] = fcmdr_obj;
        kf.get_keys(group)[0].forEach(function(key) {
            fcmdr_obj[key] = kf.get_value(group, key);
        });
    });

    this.connmgr.submit_change("org.gnome.online-accounts", JSON.stringify(result));

    return;
}

var GSettingsLogger = function (connmgr) {
    debug("Constructing GSettingsLogger");
    this.connmgr = connmgr;

    this.BUS_NAME       = 'ca.desrt.dconf';
    this.OBJECT_PATH    = '/ca/desrt/dconf/Writer/user';
    this.INTERFACE_NAME = 'ca.desrt.dconf.Writer';

    this.path_to_known_schema   = {};
    this.relocatable_schemas    = [];
    this.past_keys_for_path     = {};
    this.found_schemas_for_path = {};
    this.dconf_subscription_id  = 0;

    this.schema_source = Gio.SettingsSchemaSource.get_default();

    /* Populate a table of paths to schema ids.  We can do this up
     * front for fixed-path schemas.  For relocatable schemas we have to
     * wait for a change to occur and then try to derive the schema from
     * the path and key(s) in the change notification. */
    Gio.Settings.list_schemas().forEach(function(schema_name) {
        let schema   = this.schema_source.lookup(schema_name, true);
        let path     = schema.get_path();
        this.path_to_known_schema[path] = schema_name;
    }.bind(this));

    this.relocatable_schemas = Gio.Settings.list_relocatable_schemas();

    Gio.bus_watch_name(
        Gio.BusType.SESSION,
        this.BUS_NAME,
        Gio.BusNameWatcherFlags.NONE,
        this._bus_name_appeared_cb.bind(this),
        this._bus_name_disappeared_cb.bind(this));
}

GSettingsLogger.prototype._writer_notify_cb = function (connection, sender_name, object_path,
                                                        interface_name, signal_name, parameters) {
    let path = parameters.get_child_value(0).get_string()[0];
    let keys = [];
    let tag  = parameters.get_child_value(2).get_string()[0];
    if (!hasSuffix(path, "/")) {
      let split = path.split("/");
      keys.push(split.pop());
      path = split.join("/") + "/";
    } else {
      let keys_variant = parameters.get_child_value(1);
      for (let i = 0; i < keys_variant.n_children(); i++) {
        keys.push(keys_variant.get_child_value(i).get_string()[0]);
      }
    }
    let schema_known = false;

    debug("dconf Notify: " + path)
    debug(">>> Keys: " + keys);

    if (Object.keys(this.path_to_known_schema).indexOf(path) != -1) {
      let schema   = this.schema_source.lookup(this.path_to_known_schema[path], true);
      let settings = Gio.Settings.new_full(schema, null, null);
      this._settings_changed(schema, settings, keys);
      return;
    }

    debug(">>> Schema not known yet");
    let schema_name = this._guess_schema(path, keys);
    if (schema_name == null)
      return;
 
    let schema   = this.schema_source.lookup(schema_name, true);
    let settings = Gio.Settings.new_full (schema, null, path);
    this._settings_changed(schema, settings, keys);
}

GSettingsLogger.prototype._settings_changed = function(schema, settings, keys) {
    debug ("Submitting change for keys [" + keys + "] on schema " + schema.get_id());
    keys.forEach(function(key) {
        let variant   = settings.get_value(key);
        let builder   = new Json.Builder();
        let generator = new Json.Generator();

        builder.begin_object();
        builder.set_member_name("key");
        builder.add_string_value(settings.path + key);
        builder.set_member_name("schema");
        builder.add_string_value(schema.get_id());
        builder.set_member_name("value");
        builder.add_value(Json.gvariant_serialize(variant));
        builder.end_object();

        generator.set_root(builder.get_root());
        let data = generator.to_data(null)[0];

        this.connmgr.submit_change("org.gnome.gsettings", data);
    }.bind(this));
}


/* In this function we try to guess the schema by trying to find a
 * unique candidate that has all the keys that affect a given path.
 *
 * We could vastly improve this function if we had DConf bindings
 * to list all the keys in a given path outside of GSettings */
GSettingsLogger.prototype._guess_schema = function (path, keys) {
    if (this.found_schemas_for_path[path]) {
        let schema = this.found_schemas_for_path[path];
        debug("Schema for path " + path + " was already found: " + schema);
        return schema;
    }

    /* We store (path,keys) we didn't find a schema for in case
     * future keys might help complete the picture and allows us
     * to find a schema. */
    if (this.past_keys_for_path[path]) {
        keys = this.past_keys_for_path[path].concat(keys);
    }

    let candidates = this.relocatable_schemas.filter(function(schema_name) {
        let schema = this.schema_source.lookup(schema_name, true);
        if (schema == null)
            return false;

        return keys.every(function (key) {
            return schema.has_key(key);
        }.bind(this));
    }.bind(this));

    if (candidates.length == 1)
    {
      /* Keep the schema for this path around and discard its keys array
       * from the past_keys_for_path object as we don't need it anymore */
      this.found_schemas_for_path[path] = candidates[0];
      delete this.past_keys_for_path[path];

      debug("Schema found: " + candidates[0]);
      return candidates[0];
    }

    if (candidates.length > 1)
      debug("Too many schemas match this keyset: " + candidates);
    else
      debug("No schemas with this key were found");

    /* We keep all the keys for future attempts */
    this.past_keys_for_path[path] = keys;

    return null;
}

GSettingsLogger.prototype._bus_name_appeared_cb = function (connection, name, owner) {
    debug(this.BUS_NAME + " bus appeared");
    this.dconf_subscription_id = connection.signal_subscribe (
        owner,
        this.INTERFACE_NAME,
        'Notify',
        this.OBJECT_PATH,
        null,
        Gio.DBusSignalFlags.NONE,
        this._writer_notify_cb.bind(this),
        null);
}

GSettingsLogger.prototype._bus_name_disappeared_cb = function (connection, bus_name) {
    debug(this.BUS_NAME + " bus disappeared");

    if (this.dconf_subscription_id == 0)
      return;

    connection.signal_unsubscribe (this.dconf_subscription_id);
    this.dconf_subscription_id = 0;
}

//Something ugly to overcome the lack of exit()
options = parse_options ();

if (options != null) {
    inhibitor = new ScreenSaverInhibitor();
    let connmgr = new ConnectionManager(options['admin_server_host'], options['admin_server_port']);
    let goalogger = new GoaLogger(connmgr);
    let gsetlogger = new GSettingsLogger(connmgr);

    ml.run();
}
