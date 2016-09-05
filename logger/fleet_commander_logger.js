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

const System = imports.system;

const GLib = imports.gi.GLib;
const Gio  = imports.gi.Gio;
const Soup = imports.gi.Soup;
const Json = imports.gi.Json;

let NM   = imports.gi.NM;

//Global constants
let RETRY_INTERVAL = 1000;
let SUBMIT_PATH    = '/changes/submit/';
let DEV_PATH       = '/dev/virtio-ports/';
let DEV_PREFIX     = 'fleet-commander_';
let HOME_DIR       = GLib.get_home_dir () + "/";

//Mainloop
const ml = imports.mainloop;

//Global settings
var _debug = false;
var _use_devfile = true;

function debug (msg) {
  if (!_debug)
    return;
  printerr("DEBUG: " + msg);
}

function hasSuffix (haystack, needle) {
  return (haystack.length - needle.length) == haystack.lastIndexOf(needle);
}

function hasPrefix (haystack, needle) {
  return 0 == haystack.indexOf(needle);
}

function get_options_from_devfile () {
  let dev = Gio.file_new_for_path (DEV_PATH);
  let options = {};

  if (dev.query_exists (null) == false) {
    printerr ("No file found in " + DEV_PATH);
    return null;
  }

  let enumerator = dev.enumerate_children ("standard::name", Gio.FileQueryInfoFlags.NONE, null);
  for (let info = enumerator.next_file (null); info != null; info = enumerator.next_file (null)) {
    let name = info.get_name ();
    if (hasPrefix(info.get_name (), DEV_PREFIX)) {
      let hostport = name.slice (DEV_PREFIX.length, name.length);

      let lastdash = hostport.lastIndexOf ("-");
      if (lastdash == -1) {
        printerr (name + " file does not have '-' port separator");
        continue;
      }

      let host = hostport.slice (0, lastdash);
      let portstr = hostport.slice (lastdash + 1, hostport.length);

      let port = parseInt(portstr);

      if (port.toString() !=  portstr) {
        printerr ("Could not parse admin connection port string " + portstr + " as integer");
        continue;
      }

      debug ("Found server file in " + DEV_PATH + "fleet-commander_" + host + "-" + port);

      if (host == "localhost" || host == "127.0.0.1") {
        let route = null;
        while (route == null) {
          route = get_default_route ();
          GLib.usleep (2000000);
        }
        if (route) {
          debug ("Found " + host + " as admin host, using default route");
          host = route;
        }
      }
      options['admin_server_host'] = host;
      options['admin_server_port'] = port;

      return options;
    }
  }
  debug ("No fleet commander file in " + DEV_PATH + " to find host and port");
  return null;
}

function get_default_route () {
  let route = null;
  let ipr = Gio.Subprocess.new (["ip", "-4", "route", "list", "0/0"],
                                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);

  let pipe = ipr.get_stdout_pipe ();
  ipr.wait (null);
  let input = Gio.DataInputStream.new (pipe);
  let stdout = input.read_until ("\0", null)[0];

  if (ipr.get_exit_status () != 0) {
    printerr ("There was an error calling ip to get the default route");
  } else if (stdout == null) {
    printerr ("There were no default routes, waiting for a default route to be available");
  } else {

    let routev = stdout.trim ().split (" ");
    if (routev.length > 2) {
      route = routev[2];
    }
  }

  return route;
}

function parse_args () {
  for(let i = 0; i < ARGV.length; i++) {
    switch(ARGV[i]) {
      case "--no-devfile":
        _use_devfile = false;
        break;
      case "--help":
      case "-h":
        printerr("--no-devfile:            don't use /dev/ file for options");
        printerr("--help/-h:               show this output message");
        printerr("--debug/-d/-v:           enables debugging/verbose output");
        System.exit(0);
        break;
      case "--debug":
      case "-d":
      case "-v":
        _debug = true;
        debug("Debugging output enabled");
        break;
    }
  }
}

var ScreenSaverInhibitor = function () {
    this.proxy = Gio.DBusProxy.new_sync(Gio.DBus.session, Gio.DBusProxyFlags.NONE, null,
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

ConnectionManager.prototype.give_up = function () {
  this.queue = [];
  if (this.timeout == 0)
    return;

  GLib.source_remove(this.timeout);
  this.timeout = 0;
}

/* TODO: This function will commit batches of changes in a single request */
ConnectionManager.prototype.finish_changes = function () {
}

// Generic
var FileMonitor = function(path, callback) {
    this.monitor = Gio.File.new_for_path(path).monitor_file(Gio.FileMonitorFlags.NONE, null);
    this.monitor.connect ('changed', callback);
}

var NMLogger = function (connmgr) {
    debug("Constructing NetworkManager logger");
    this.connmgr = connmgr;
    this.nmclient = NM.Client.new (null);
    this.nmclient.connect ('connection-added', this.connection_added_cb.bind(this));
}

NMLogger.prototype.security_filter = function (conn) {
    conn = this.filter_variant (conn, ['connection', 'permissions']);
    conn = this.filter_variant (conn, ['vpn','data','secrets','Xauth password']);
    conn = this.filter_variant (conn, ['vpn','data','secrets','password']);
    conn = this.filter_variant (conn, ['802-1x','password']);
    conn = this.filter_variant (conn, ['802-11-wireless-security','leap-password']);
    return conn;
}

NMLogger.prototype.filter_variant  = function (variant, filter) {
    debug ("Filtering: " + filter);
    let is_variant = variant.get_type_string () == "v";

    if (is_variant)
      variant = variant.get_child_value (0);

    let dict_type = new GLib.VariantType ("a{s*}");

    if ((filter.length < 1) ||
        (variant.is_of_type (dict_type) == false) ||
        (variant.n_children () < 1) ||
        (variant.lookup_value (filter[0], null) == null)) {
        if (is_variant)
            return new GLib.Variant ("v", variant);
        return variant;
    }

    let dict = GLib.VariantBuilder.new (variant.get_type ());
    for (let i = 0; i < variant.n_children (); i++) {
        let child = variant.get_child_value (i);

        let key = child.get_child_value(0).get_string ()[0];

        if (key != filter[0]) {
            dict.add_value (child);
            continue;
        }

        if (filter.length == 1)
            continue;

        let child_builder = GLib.VariantBuilder.new (child.get_type ());
        child_builder.add_value (child.get_child_value (0));
        child_builder.add_value (this.filter_variant (child.get_child_value (1),
                                                      filter.slice (1)));
        dict.add_value (child_builder.end ());
    }

    if (is_variant)
        return new GLib.Variant ("v", dict.end ());
    return dict.end ();
}

NMLogger.prototype.merge_variants = function (va, vb) {
    debug ("Merging variants");
    let are_variants = va.get_type_string () == "v" && vb.get_type_string () == "v";
    if (are_variants) {
        va = va.get_child_value (0);
        vb = vb.get_child_value (0);
    }

    if (va.get_type_string () != vb.get_type_string ()) {
        printerr ("Can't merge variants of different types");
        if (are_variants)
            return new GLib.Variant ("v", va);
        return va;
    }

    let dict_type = new GLib.VariantType ("a{s*}");

    if (va.is_of_type (dict_type) == false) {
        if (are_variants)
            return new GLib.Variant ("v", vb);
        return vb;
    }

    let builder = GLib.VariantBuilder.new (va.get_type ());
    for (let i = 0; i < va.n_children (); i++) {
        let child_a = va.get_child_value (i);
        let key = child_a.get_child_value (0).get_string ()[0];

        let value_b = vb.lookup_value (key, null);
        if (value_b == null) {
            builder.add_value (child_a);
            continue;
        }

        let value_a = va.lookup_value (key, null);
        let merge = this.merge_variants (value_a, value_b);

        let child_builder = GLib.VariantBuilder.new (child_a.get_type ());
        child_builder.add_value (child_a.get_child_value (0));
        if (child_a.get_child_value (1).get_type_string () == "v" &&
            merge.get_type_string () != "v")
          merge = new GLib.Variant ("v", merge);
        child_builder.add_value (merge);
        builder.add_value (child_builder.end ());
    }

    for (let i = 0; i < vb.n_children (); i++) {
        let child = vb.get_child_value (i);
        let key = child.get_child_value (0).get_string()[0];

        if (va.lookup_value (key, null) != null)
            continue;

        builder.add_value (child);
    }

    if (are_variants)
        return GLib.Variant ("v", builder.end ());
    return builder.end ();
}

NMLogger.prototype.submit_connection = function (conn) {
    debug ("Submitting Network Manager connection");
    let conf = conn.to_dbus (NM.ConnectionSerializationFlags.ALL);
    let type = conn.get_connection_type ();
    let secrets = [];

    debug ("Added connection of type " + type);

    if (  type == "802-11-wireless") {
        /* Looks like this triggers an infinite loop */
        try { secrets.push (conn.get_secrets ("802-11-wireless-security", null)); }
        catch (e) {}
        try { secrets.push (conn.get_secrets ("802-1x", null)); } // we might not want this, ever
        catch (e) {}
    } else if (type == "vpn") {
        try { secrets.push (conn.get_secrets ("vpn", null)); }
        catch (e) {}
    } else if (type == "802-3-ethernet")  {
        try { secrets.push (conn.get_secrets ("802-1x", null)); } // we might not want this, ver
        catch (e) {}
    } else {
        debug ("Network Connection discarded as type " + type + " is not supported");
        return;
    }

    for (let s in secrets) {
      conf = this.merge_variants (conf, secrets[s]);
    }

    conf = this.security_filter (conf);

    let payload = {
      data: conf.print (true),
      uuid: null,
      type: null,
      id: null,
    }

    let connection = conf.lookup_value ("connection", null);
    if (connection != null) {
      payload.uuid = connection.lookup_value ("uuid", null).get_string ()[0];
      payload.type = connection.lookup_value ("type", null).get_string ()[0];
      payload.id   = connection.lookup_value ("id", null).get_string ()[0];
    }

    this.connmgr.submit_change ("org.freedesktop.NetworkManager", JSON.stringify (payload));
    this.connmgr.finish_changes();
}

//This is a workaround for the broken deep_unpack behaviour
NMLogger.prototype.deep_unpack = function (variant) {
    let unpack_internal = function (unpack) {
        if (unpack instanceof GLib.Variant) {
          return unpack_internal (unpack.deep_unpack ());
        }

        if ((unpack instanceof Array) || (unpack instanceof Object)) {
            for (let e in unpack) {
                unpack[e] = unpack_internal (unpack[e]);
            }
        }

        return unpack;
    }.bind (this);

    return unpack_internal (variant);
}

NMLogger.prototype.merge_confs = function (conf, secrets) {
    if (!(conf instanceof Object) || !(secrets instanceof Object)) {
       printerr ("ERROR: Cannot merge two items that aren't objects: " +conf+ " " +secrets);
       return {};
    }

    debug ("Merging " + JSON.stringify(conf) + " and " + JSON.stringify (secrets));

    for (let group in secrets) {
        if (!(group in conf)) {
            conf[group] = secrets[group];
            continue;
        }

        for (let key in secrets[group]) {
            if (conf[group][key] instanceof Object) {
                conf[group][key] = this.merge_confs(conf[group][key],
                                                    secrets[group][key]);
                continue;
            }
            conf[group][key] = secrets[group][key];
        }
    }

    return conf;
}

NMLogger.prototype.connection_added_cb = function (client, connection) {
    debug("Network Manager connection added");
    this.submit_connection (connection);
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

    /* Create file for LibreOffice dconf writes */
    let dconfwrite = Gio.File.new_for_path (HOME_DIR + ".config/libreoffice/dconfwrite");

    if (dconfwrite.query_exists (null) == false) {
      GLib.mkdir_with_parents (dconfwrite.get_parent ().get_path (), 483);
      try {
        dconfwrite.create (Gio.FileCreateFlags.NONE, null);
      } catch (e) {
        printerr ("Could not create file " + dconfwrite.get_path () + ": " + e.message);
      }
    }

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

  if (hasPrefix(path, "/org/libreoffice/registry")) {
    debug (">>> LibreOffice configuration change detected, no schema search needed");
    this._libreoffice_change (path, keys);
    return;
  }

  if (Object.keys(this.path_to_known_schema).indexOf(path) != -1) {
    let schema   = this.schema_source.lookup(this.path_to_known_schema[path], true);
    let settings = Gio.Settings.new_full(schema, null, null);
    this._settings_changed(schema, settings, keys);
    return;
  }

  debug(">>> Schema not known yet");
  let schema_name = this._guess_schema(path, keys);
  if (schema_name == null) {
    this.connmgr.finish_changes();
    return;
  }

  let schema   = this.schema_source.lookup(schema_name, true);
  let settings = Gio.Settings.new_full (schema, null, path);
  this._settings_changed(schema, settings, keys);
}

GSettingsLogger.prototype._libreoffice_change = function(path, keys) {
  debug ("Submitting LibreOffice change for keys [" + keys + "] for path " + path);

  keys.forEach(function(key) {
    let builder   = new Json.Builder();
    let generator = new Json.Generator();

    let command = ["dconf", "read", path + key];
    let dconf = Gio.Subprocess.new (command, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
    let stdout_pipe = dconf.get_stdout_pipe();
    dconf.wait(null);
    if (dconf.get_exit_status() != 0) {
      printerr ("There was an error calling dconf subprocess with arguments: " + command);
      return;
    }

    /* FIXME: libdconf doesn't have introspection support, we call dconf manually */
    let data = Gio.DataInputStream.new (stdout_pipe);
    let variant_string = data.read_until ("\0", null)[0];

    if (variant_string == null) {
      printerr ("There was an error reading dconf key " + path + key);
      return;
    }

    if (hasSuffix(variant_string, "\n")) {
      variant_string = variant_string.substring(0, variant_string.length - 1);
    }

    let variant = null;
    try {
       variant = GLib.Variant.parse(null, variant_string, null, null);
    } catch (e) {
      printerr ("There was an error parsing the variant string from the dconf read output for '" + path + key + "':");
      printerr (variant_string);
      return;
    }

    builder.begin_object();
    builder.set_member_name("key");
    builder.add_string_value(path + key);
    builder.set_member_name("value");
    builder.add_value(Json.gvariant_serialize(variant));
    builder.set_member_name("signature");
    builder.add_string_value(variant.get_type_string());
    builder.end_object();

    generator.set_root(builder.get_root());
    let data = generator.to_data(null)[0];

    this.connmgr.submit_change ("org.libreoffice.registry", data);
    this.connmgr.finish_changes ();
  }.bind(this));
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
        builder.set_member_name("signature");
        builder.add_string_value(variant.get_type().dup_string());
        builder.end_object();

        generator.set_root(builder.get_root());
        let data = generator.to_data(null)[0];

        this.connmgr.submit_change("org.gnome.gsettings", data);
    }.bind(this));
    this.connmgr.finish_changes();
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

if (GLib.getenv('FC_TESTING') == null) {
  parse_args ();
  let options = null;
  if (_use_devfile) {
    options = get_options_from_devfile (options);
    if (options == null) {
      System.exit(0);
    }
  } else {
    options = {admin_server_port: 9999, admin_server_host: 'localhost'};
  }

  debug ("admin_server_host: " + options['admin_server_host'] + " - admin_server_port: " + options['admin_server_port']);

  let inhibitor = new ScreenSaverInhibitor();
  let connmgr = new ConnectionManager(options['admin_server_host'], options['admin_server_port']);
  let gsetlogger = new GSettingsLogger(connmgr);
  let nmlogger = new NMLogger (connmgr);

  ml.run();
}
