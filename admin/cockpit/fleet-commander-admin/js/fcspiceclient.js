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

/*jslint nomen:true */
/*jslint browser:true */
/*global $ */
/*global _ */
/*global cockpit */
/*global DEBUG */
/*global spinnerDialog */
/*global messageDialog */
/*global fc */
/*global spicehtml5_module */



"use strict";


function FleetCommanderSpiceClient(details, error_cb, timeout) {
    var self = this;

    this.conn_timeout = timeout || 15000; //ms
    // this.sc;
    this.connecting = null;
    this.noretry = false;

    this.stop = function () {
        if (self.sc) {
            self.sc.stop();
        }
    };

    this.set_connection_timeout = function () {
        if (!self.connecting) {
            self.connecting = setTimeout(function () {
                if (self.sc) {
                    self.sc.stop();
                }
                $('#spice-screen').html('');
                self.connecting = null;
                self.noretry = true;
                if (DEBUG > 0) {
                    console.log('FC: Connection tries timed out');
                }
                spinnerDialog.close();
                messageDialog.show(
                    _('Connection error to virtual machine.'),
                    _('Connection error')
                );
            }, self.conn_timeout);
        }
    };

    this.spice_connected = function () {
        if (DEBUG > 0) {
            console.log('FC: Connected to virtual machine using SPICE');
        }
        spinnerDialog.close();
        if (self.connecting) {
            clearTimeout(self.connecting);
            self.connecting = null;
        }
    };

    this.spice_error = function (err) {
        if (DEBUG > 0) {
            console.log('FC: SPICE connection error:', err.message);
        }

        fc.IsSessionActive('', function (resp) {
            if (DEBUG > 0) {
                console.log('FC: Current session active status:', resp);
            }
            if (resp) {
                self.set_connection_timeout();
                if (err.message === 'Unexpected close while ready' ||
                        err.message === 'Connection timed out.' ||
                        self.sc.state !== 'ready') {
                    if (!self.noretry) {
                        spinnerDialog.show(
                            _('Connecting to virtual machine. Please wait...'),
                            _('Reconnecting')
                        );
                        self.do_connection();
                    }
                    return;
                }
                messageDialog.show(
                    _('Connection error to virtual machine'),
                    _('Connection error')
                );
            } else {
                messageDialog.show(
                    _('Virtual machine has been stopped'),
                    _('Connection error')
                );
            }

            spinnerDialog.close();
            if (self.connecting) {
                clearTimeout(self.connecting);
                self.connecting = null;
            }

        });
    };

    this.do_connection = function () {
        if (DEBUG > 0) {
            console.log('FC: Connecting to spice session');
        }

        var query = window.btoa(
                JSON.stringify({
                    payload: 'stream',
                    protocol: 'binary',
                    unix: details.path,
                    binary: 'raw',
                })
            ),
            websocket_proto = 'ws:',
            cockpit_uri;

        if (location.protocol === 'https:') {
            websocket_proto = 'wss:';
        }

        cockpit_uri = websocket_proto + '//' + location.hostname + ':' + location.port + '/cockpit/channel/' + cockpit.transport.csrf_token + '?' + query;

        if (DEBUG > 0) {
            console.log('FC: Cockpit channel websocket uri is:', cockpit_uri);
        }

        if (self.sc) {
            self.sc.stop();
        }
        $('#spice-screen').html('');

        self.sc = new spicehtml5_module.SpiceMainConn({
            uri: cockpit_uri, // 'ws://' + location.hostname + ':' + port,
            password: details.ticket,
            screen_id: 'spice-screen',
            onsuccess: self.spice_connected,
            onerror: self.spice_error
        });
    };

    try {
        self.do_connection();
    } catch (e) {
        console.error('FC: Fatal error:' + e.toString());
        if (error_cb) {
            error_cb();
        }
    }

    this.reconnect = function () {
        spinnerDialog.show(
            _('Connecting to virtual machine. Please wait...'),
            _('Reconnecting')
        );
        self.do_connection();
    };
}
