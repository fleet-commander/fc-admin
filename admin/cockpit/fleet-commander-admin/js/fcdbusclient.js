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

function FleetCommanderDbusClient(readycb, errorcb) {
    var self = this;
    var errorhandler = errorcb || function (err) {
        console.log('FC: Error - ' + err);
    };

    this._service = cockpit.dbus('org.freedesktop.FleetCommander', { bus: 'session' });
    this._proxy = this._service.proxy();

    this._proxy.wait().done(function (resp) {
        console.log('FC: Dbus service loaded');
        readycb(resp);
    }).fail(function (err) {
        console.log('FC: Failed to connect to Dbus service');
        errorhandler(err);
    });

    // Initialization methods
    this.GetInitialValues = function (cb) {
        self._proxy.GetInitialValues().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.DoDomainConnection = function (cb) {
        self._proxy.DoDomainConnection().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.HeartBeat = function (cb) {
        self._proxy.HeartBeat().done(
            function (resp) {
                cb(resp);
            }
        ).fail(errorhandler);
    };

    // Hypervisor configuration methods
    this.GetHypervisorConfig = function (cb) {
        self._proxy.GetHypervisorConfig().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.CheckHypervisorConfig = function (data, cb) {
        self._proxy.CheckHypervisorConfig(JSON.stringify(data)).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SetHypervisorConfig = function (data, cb) {
        self._proxy.SetHypervisorConfig(JSON.stringify(data)).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.CheckKnownHost = function (hostname, cb) {
        self._proxy.CheckKnownHost(hostname).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.AddKnownHost = function (hostname, cb) {
        self._proxy.AddKnownHost(hostname).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.InstallPubkey = function (hostname, user, pass, cb) {
        self._proxy.InstallPubkey(hostname, user, pass).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.GetGlobalPolicy = function (cb) {
        self._proxy.GetGlobalPolicy().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SetGlobalPolicy = function (policy, cb) {
        self._proxy.SetGlobalPolicy(policy).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    // Profile management methods
    this.GetProfiles = function (cb) {
        self._proxy.GetProfiles().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.GetProfile = function (uid, cb) {
        self._proxy.GetProfile(uid).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.DeleteProfile = function (uid, cb) {
        self._proxy.DeleteProfile(uid).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SaveProfile = function (data, cb) {
        self._proxy.SaveProfile(JSON.stringify(data)).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    // Favourites management methods
    this.HighlightedApps = function (data, uid, cb) {
        self._proxy.HighlightedApps(JSON.stringify(data), uid).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    // Live session methods
    this.ListDomains = function (cb) {
        self._proxy.ListDomains().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SessionStart = function (uuid, cb) {
        self._proxy.SessionStart(uuid).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SessionStop = function (cb) {
        self._proxy.SessionStop().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.SessionSave = function (uid, changesets, cb) {
        self._proxy.SessionSave(uid, JSON.stringify(changesets)).done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    this.IsSessionActive = function (uid, cb) {
        uid = uid || '';
        self._proxy.IsSessionActive(uid).done(
            function (resp) {
                cb(resp);
            }
        ).fail(errorhandler);
    };

    // GOA methods
    this.GetGOAProviders = function (cb) {
        self._proxy.GetGOAProviders().done(
            function (resp) {
                cb(JSON.parse(resp));
            }
        ).fail(errorhandler);
    };

    // Quit method
    this.Quit = function (cb) {
        self._proxy.Quit().done(cb).fail(errorhandler);
    };
}

export { FleetCommanderDbusClient };
