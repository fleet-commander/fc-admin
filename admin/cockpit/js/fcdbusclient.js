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
 * Authors: Alberto Ruiz <aruiz@redhat.com>
 *          Oliver Gutiérrez <ogutierrez@redhat.com>
 */

function FleetCommanderDbusClient(errorcb) {
  var self = this;

  this._service = cockpit.dbus('org.freedesktop.FleetCommander');
  this._proxy = this._service.proxy();

  this._check_dbus_loaded = function(cb) {
    if (self._proxy.GetHypervisorConfig != undefined) {
      cb()
    } else {
      setTimeout(self._check_dbus_loaded, 100, cb);
    }
  };

  this._errorhandler = errorcb || function(err) {
    console.log(err);
  };

  // Decorator for safe dbus execution
  function safe_dbus(fn){
    return function() {
      var args = arguments
      var self_dbus = this

      function check_loop(func) {
        if (self._proxy.GetHypervisorConfig != undefined) {
          return fn.apply(self_dbus, args)
        } else {
          setTimeout(check_loop, 100, func);
        }
      }
      check_loop(fn);
    };
  };

  // Hypervisor configuration methods
  this.GetHypervisorConfig = safe_dbus(function(cb, errcb) {
    self._proxy.GetHypervisorConfig().done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.SetHypervisorConfig = safe_dbus(function(data, cb, errcb) {
    self._proxy.SetHypervisorConfig(JSON.stringify(data)).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  // Profile management methods
  this.GetProfiles = safe_dbus(function(cb, errcb) {
    self._proxy.GetProfiles().done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.GetProfile = safe_dbus(function(uid, cb, errcb) {
    self._proxy.GetProfile(uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.GetProfileApplies = safe_dbus(function(uid, cb, errcb) {
    self._proxy.GetProfileApplies(uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.NewProfile = safe_dbus(function(data, cb, errcb) {
    self._proxy.NewProfile(JSON.stringify(data)).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.DeleteProfile = safe_dbus(function(uid, cb, errcb) {
    self._proxy.DeleteProfile(uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.ProfileProps = safe_dbus(function(data, uid, cb, errcb) {
    self._proxy.ProfileProps(JSON.stringify(data), uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  // Favourites management methods
  this.HighlightedApps = safe_dbus(function(data, uid, cb, errcb) {
    self._proxy.HighlightedApps(JSON.stringify(data), uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  // Live session methods
  this.ListDomains = safe_dbus(function(cb, errcb) {
    self._proxy.ListDomains().done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.SessionStart = safe_dbus(function(uuid, host, cb, errcb) {
    self._proxy.SessionStart(uuid, host).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.SessionStop = safe_dbus(function(cb, errcb) {
    self._proxy.SessionStop().done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.SessionSave = safe_dbus(function(uid, cb, errcb) {
    self._proxy.SessionSave(uid).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  // Changes methods
  this.GetChanges = safe_dbus(function(cb, errcb) {
    self._proxy.GetChanges().done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

  this.SelectChanges = safe_dbus(function(data, cb, errcb) {
    self._proxy.SelectChanges(JSON.stringify(data)).done(
      function(resp) {
        cb(JSON.parse(resp));
      }
    ).fail(errcb || self._errorhandler);
  });

}
