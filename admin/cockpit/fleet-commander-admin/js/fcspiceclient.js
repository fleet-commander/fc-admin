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

import { DEBUG } from './base.js';
import { SpinnerDialog, MessageDialog } from './dialogs.js';
import * as SpiceHtml5 from './spice-html5/src/main.js';

const _ = cockpit.gettext;

function FleetCommanderSpiceClient(details, error_cb, spice_error_cb, timeout) {
    const self = this;

    this.conn_timeout = timeout || 15000; // ms
    // this.sc;
    this.connecting = null;
    this.noretry = false;
    this.messageDialog = new MessageDialog();
    this.spinnerDialog = new SpinnerDialog();

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
                self.spinnerDialog.close();
                self.messageDialog.show(
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
        self.spinnerDialog.close();
        if (self.connecting) {
            clearTimeout(self.connecting);
            self.connecting = null;
        }
    };

    this.spice_error = err => {
        if (spice_error_cb) {
            spice_error_cb(err);
        }
    };

    this.do_connection = function () {
        if (DEBUG > 0) {
            console.log('FC: Connecting to spice session');
        }

        const query = window.btoa(
            JSON.stringify({
                payload: 'stream',
                protocol: 'binary',
                unix: details.path,
                binary: 'raw',
            })
        );

        let websocket_proto = 'ws:';
        if (location.protocol === 'https:') {
            websocket_proto = 'wss:';
        }

        const cockpit_uri = websocket_proto + '//' +
                            location.hostname +
                            ':' + location.port +
                            '/cockpit/channel/' +
                            cockpit.transport.csrf_token +
                            '?' + query;

        if (DEBUG > 0) {
            console.log('FC: Cockpit channel websocket uri is:', cockpit_uri);
        }

        if (self.sc) {
            self.sc.stop();
        }
        $('#spice-screen').html('');

        self.sc = new SpiceHtml5.SpiceMainConn({
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
        self.spinnerDialog.show(
            _('Connecting to virtual machine. Please wait...'),
            _('Reconnecting')
        );
        self.do_connection();
    };
}

export { FleetCommanderSpiceClient };
