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

import { DEBUG, setDebugLevel } from './base.js';
import { BaseCollector, NMCollector, FirefoxBookmarksCollector } from './collectors.js';
import { spinnerDialog, messageDialog, showCurtain } from './dialogs.js';
import { FleetCommanderDbusClient } from './fcdbusclient.js';
import { FleetCommanderSpiceClient } from './fcspiceclient.js';
import { arraybuffer_to_str } from './spice-html5/src/utils.js';

const FC_MSG_DELIM = ':FC_MSG_END_DATA:';
const FC_PROTO_HEADER = ':FC_PR:';
const FC_PROTO_DEFAULT = 1;
const _ = cockpit.gettext;

let fc = null;
let fcsc = null;
let console_details = null;
const collectors = {
    'org.gnome.gsettings':
        new BaseCollector('org.gnome.gsettings'),
    'org.libreoffice.registry':
        new BaseCollector('org.libreoffice.registry'),
    'org.chromium.Policies':
        new BaseCollector('org.chromium.Policies'),
    'com.google.chrome.Policies':
        new BaseCollector('com.google.chrome.Policies'),
    'org.mozilla.firefox':
        new BaseCollector('org.mozilla.firefox'),
    'org.mozilla.firefox.Bookmarks':
        new FirefoxBookmarksCollector('org.mozilla.firefox.Bookmarks'),
    'org.freedesktop.NetworkManager':
        new NMCollector('org.freedesktop.NetworkManager')
};

window.alert = function (message) {
    if (DEBUG > 0) {
        console.log('FC: Alert message:' + message);
    }
};

function downloadConnectionFile(console_details) {
    console.log("Generate remote-viewer connection file: ", console_details);
    const data = '[virt-viewer]\n' +
        `type=${console_details.type}\n` +
        `host=${console_details.address}\n` +
        `tls-port=${console_details.tls_port}\n` +
        `password=${console_details.ticket}\n` +
        `ca=${console_details.ca_cert}\n` +
        `host-subject=${console_details.cert_subject}\n` +
        'delete-this-file=1\n' +
        'secure-channels=all\n' +
        'fullscreen=0\n';

    const f = document.createElement('iframe');
    f.width = '1';
    f.height = '1';
    document.body.appendChild(f);
    f.src = `data:application/x-virt-viewer,${encodeURIComponent(data)}`;
}

function ParseChange(data) {
    console.log('FC: Parsing data', data);
    try {
        const change = JSON.parse(data);
        if (DEBUG > 0) {
            console.log('FC: Change parsed', change);
        }
        if (collectors[change.ns] !== undefined) {
            collectors[change.ns].handle_change(JSON.parse(change.data));
        } else {
            if (DEBUG > 0) {
                console.log('FC: Unknown change namespace', change.ns);
            }
        }
    } catch (e) {
        if (DEBUG > 0) {
            console.log('FC: Error while parsing change', data);
        }
        stopLiveSession(() => {
            messageDialog.show(
                _('Error parsing change'),
                _('Error'),
                () => { location.href = 'index.html' }
            );
        });
    }
}

function startSpiceHtml5(conn_details) {
    // SPICE port changes listeners
    const msg = {
        buffer: '',
        initial_msg: true,
        fc_proto_version: FC_PROTO_DEFAULT,
    };
    window.addEventListener('spice-port-data', function (event) {
        if (event.detail.channel.portName === 'org.freedesktop.FleetCommander.0') {
            const msg_text = arraybuffer_to_str(new Uint8Array(event.detail.data));
            if (DEBUG > 0) {
                console.log(
                    'FC: Logger data received in spice port',
                    event.detail.channel.portName,
                );
            }
            parseFCMsg(msg_text, msg);
        }
    });

    window.addEventListener('spice-port-event', function (event) {
        if (event.detail.channel.portName === 'org.freedesktop.FleetCommander.0') {
            if (event.detail.spiceEvent[0] === 0) {
                if (DEBUG > 0) {
                    console.log('FC: Logger connected to SPICE channel');
                }
            } else if (event.detail.spiceEvent[0] === 1) {
                if (DEBUG > 0) {
                    console.log('FC: Logger disconnected from SPICE channel');
                }
                stopLiveSession();
            } else {
                if (DEBUG > 0) {
                    console.log(
                        'FC: Unknown event received in SPICE channel',
                        event.detail.spiceEvent
                    );
                }
            }
        }
    });

    const details = {
        path: conn_details.path,
        ticket: conn_details.ticket,
    };

    fcsc = new FleetCommanderSpiceClient(
        details, stopLiveSession, reconnectSpice
    );
    startHeartBeat();
}

function startRemoteViewer(conn_details) {
    console_details = {
        type: 'spice',
        address: conn_details.host,
        tls_port: conn_details.tls_port,
        ca_cert: conn_details.ca_cert.replace(/\n/g, "\\n"),
        cert_subject: conn_details.cert_subject,
        ticket: conn_details.ticket,
    };
    downloadConnectionFile(console_details);

    const options = {
        payload: 'stream',
        protocol: 'binary',
        batch: 2048,
        unix: conn_details.notify_socket,
        binary: true,
    };
    const channel = cockpit.channel(options);

    const msg = {
        buffer: '',
        initial_msg: true,
        fc_proto_version: FC_PROTO_DEFAULT,
    };

    channel.addEventListener("ready", function(event, options) {
        if (DEBUG > 0) {
            console.log('FC: Cockpit changes channel is open');
        }
    });
    channel.addEventListener("message", function(event, data) {
        const msg_text = arraybuffer_to_str(new Uint8Array(data));
        if (DEBUG > 0) {
            console.log('FC: Logger data received in unix channel', data);
        }
        parseFCMsg(msg_text, msg);
    });
    channel.addEventListener("close", function(event, options) {
        if (DEBUG > 0) {
            console.log('FC: Cockpit changes channel is closed', options);
        }
        stopLiveSession();
    });

    startHeartBeat();
}

function parseFCMsg(str, msg) {
    /*
     * Protocol 1 assumes atomic data transmission
     * Protocol 2 process data in chunks
     */
    if (DEBUG > 0) {
        console.log('FC: Processing msg, length:%s', str.length);
    }
    if (str === '') {
        // nothing to do
        return;
    }

    if (msg.buffer) {
        str = msg.buffer + str;
    }

    if (msg.initial_msg === true) {
        // detecting protocol version
        if (DEBUG > 0) {
            console.log('FC: Initial message processing');
        }
        // receive enough characters
        if (str.startsWith(':') && str.length < FC_PROTO_HEADER.length) {
            msg.buffer = str;
            return;
        }

        const fc_proto_header = str.match(/^:FC_PR:/);
        if (fc_proto_header === null) {
            msg.fc_proto_version = FC_PROTO_DEFAULT;
            if (DEBUG > 0) {
                console.log('FC: old fc_proto detected', msg.fc_proto_version);
            }
            msg.buffer = '';
        } else {
            const fc_proto = str.match(/(^:FC_PR:(\d+):)/);
            if (fc_proto === null) {
                // continue receving
                msg.buffer = str;
                return;
            }
            msg.fc_proto_version = parseInt(fc_proto[2]);
            // cut off the proto header
            str = str.replace(/^:FC_PR:\d+:/, '');
        }
        if (DEBUG > 0) {
            console.log('FC protocol version', msg.fc_proto_version);
        }
        msg.initial_msg = false;
    }

    if (msg.fc_proto_version > FC_PROTO_DEFAULT) {
        const last_delimiter = str.lastIndexOf(FC_MSG_DELIM);
        if (last_delimiter === -1) {
            msg.buffer = str;
            if (DEBUG > 0) {
                console.log('FC: Waiting for FC_MSG_DELIM');
            }
            return;
        }
        msg.buffer = str.substring(last_delimiter + FC_MSG_DELIM.length);

        str = str.substring(0, last_delimiter);
        const lines = str.split(FC_MSG_DELIM);
        lines.forEach((line) => {
            if (line) {
                ParseChange(line);
            }
        });
    } else if (msg.fc_proto_version === FC_PROTO_DEFAULT) {
        ParseChange(str);
    }
}

function startHeartBeat() {
    window.setInterval(function () {
        fc.HeartBeat(resp => {});
    }, 1000);
}

function stopLiveSession(cb) {
    if (fcsc) {
        fcsc.stop();
    }
    fc.SessionStop(function () {
        if (typeof cb === 'function') {
            cb();
        } else {
            location.href = 'index.html';
        }
    });
}

function reconnectSpice(err) {
    if (DEBUG > 0) {
        console.log('FC: SPICE connection error:', err.message);
    }

    fc.IsSessionActive('', function (resp) {
        if (DEBUG > 0) {
            console.log('FC: Current session active status:', resp);
        }
        if (resp) {
            fcsc.set_connection_timeout();
            if (err.message === 'Unexpected close while ready' ||
                    err.message === 'Connection timed out.' ||
                    fcsc.sc.state !== 'ready') {
                if (!fcsc.noretry) {
                    spinnerDialog.show(
                        _('Connecting to virtual machine. Please wait...'),
                        _('Reconnecting')
                    );
                    fcsc.do_connection();
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
        if (fcsc.connecting) {
            clearTimeout(fcsc.connecting);
            fcsc.connecting = null;
        }
    });
}

function startLiveSession() {
    spinnerDialog.show(
        _('Connecting to virtual machine')
    );
    // Stop any previous session
    stopLiveSession(function () {
        const domain = sessionStorage.getItem("fc.session.domain");
        fc.SessionStart(domain, function (resp) {
            if (resp.status) {
                const conn_details = resp.connection_details;
                const viewers = {
                    spice_html5: startSpiceHtml5,
                    spice_remote_viewer: startRemoteViewer,
                };
                if (conn_details.viewer in viewers === false) {
                    messageDialog.show(
                        _('Not supported libvirt viewer:' + conn_details.viewer),
                        _('Error'));
                    spinnerDialog.close();
                    return;
                }
                spinnerDialog.close();
                viewers[conn_details.viewer](conn_details);
            } else {
                messageDialog.show(resp.error, _('Error'));
                spinnerDialog.close();
            }
        });
    });
}

function reconnectToVM() {
    if (fcsc) {
        fcsc.reconnect();
    } else if (console_details) {
        downloadConnectionFile(console_details);
    }
}

function addSectionCheckbox(section) {
    const section_header = $(section).prev("h4");
    const chkbox_container = $(
        '<div/>',
        {
            class: 'list-view-pf-checkbox',
            id: section.replace("#", "") + '-chkbox-container'
        }
    );
    const checkbox = $('<input/>', { type: 'checkbox' });

    checkbox.click(function () {
        const sectionChecked = this.checked;
        $(section).find('input[type=checkbox]').each(function () {
            this.checked = sectionChecked;
        });
    });
    chkbox_container.append(checkbox);
    chkbox_container.insertBefore(section_header);
}

function removeSectionCheckbox(section) {
    $(section + '-chkbox-container').remove();
}

function populateSectionChanges(section, data, only_value) {
    $.each(data, function (unusedIndex, item) {
        const citem = $($('#change-item-template').html());
        let row;

        if (only_value) {
            row = item[1];
        } else {
            row = item.join(" ");
        }

        citem.appendTo($(section));
        const checkbox = citem.find('input[type=checkbox]');
        checkbox.attr('data-id', item[0]);
        citem.find('.changekey').html(row);
    });
    removeSectionCheckbox(section);
    if (data.length) {
        addSectionCheckbox(section);
    }
}

function populateChanges() {
    $('#gsettings-event-list').html('');
    $('#libreoffice-event-list').html('');
    $('#chromium-event-list').html('');
    $('#chrome-event-list').html('');
    $('#firefox-event-list').html('');
    $('#firefoxbookmarks-event-list').html('');
    $('#networkmanager-event-list').html('');

    if (DEBUG > 0) {
        console.log('FC: Populating LibreOffice change list');
    }
    populateSectionChanges(
        '#libreoffice-event-list',
        collectors['org.libreoffice.registry'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating GSettings change list');
    }
    populateSectionChanges(
        '#gsettings-event-list',
        collectors['org.gnome.gsettings'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating Chromium change list');
    }
    populateSectionChanges(
        '#chromium-event-list',
        collectors['org.chromium.Policies'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating Chrome change list');
    }
    populateSectionChanges(
        '#chrome-event-list',
        collectors['com.google.chrome.Policies'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating Firefox change list');
    }
    populateSectionChanges(
        '#firefox-event-list',
        collectors['org.mozilla.firefox'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating Firefox bookmarks change list');
    }
    populateSectionChanges(
        '#firefoxbookmarks-event-list',
        collectors['org.mozilla.firefox.Bookmarks'].dump_changes()
    );

    if (DEBUG > 0) {
        console.log('FC: Populating NetworkManager change list');
    }
    populateSectionChanges(
        '#networkmanager-event-list',
        collectors['org.freedesktop.NetworkManager'].dump_changes()
    );
}

function reviewAndSubmit() {
    $('.change-checkbox').show();
    populateChanges();
    $('#event-logs').modal('show');
}

function deployProfile() {
    const gsettings = [];
    const libreoffice = [];
    const chromium = [];
    const chrome = [];
    const firefox = [];
    const firefoxbookmarks = [];
    const networkmanager = [];

    $.each($('#gsettings-event-list input[data-id]:checked'), function (i, e) {
        gsettings.push($(this).attr('data-id'));
    });

    $.each($('#libreoffice-event-list input[data-id]:checked'), function (i, e) {
        libreoffice.push($(this).attr('data-id'));
    });

    $.each($('#chromium-event-list input[data-id]:checked'), function (i, e) {
        chromium.push($(this).attr('data-id'));
    });

    $.each($('#chrome-event-list input[data-id]:checked'), function (i, e) {
        chrome.push($(this).attr('data-id'));
    });

    $.each($('#firefox-event-list input[data-id]:checked'), function (i, e) {
        firefox.push($(this).attr('data-id'));
    });

    $.each($('#firefoxbookmarks-event-list input[data-id]:checked'), function (i, e) {
        firefoxbookmarks.push($(this).attr('data-id'));
    });

    $.each($('#networkmanager-event-list input[data-id]:checked'), function (i, e) {
        networkmanager.push($(this).attr('data-id'));
    });

    const changesets = {
        'org.gnome.gsettings':
            collectors['org.gnome.gsettings'].get_changeset(gsettings),
        'org.libreoffice.registry':
            collectors['org.libreoffice.registry'].get_changeset(libreoffice),
        'org.chromium.Policies':
            collectors['org.chromium.Policies'].get_changeset(chromium),
        'com.google.chrome.Policies':
            collectors['com.google.chrome.Policies'].get_changeset(chrome),
        'org.mozilla.firefox':
            collectors['org.mozilla.firefox'].get_changeset(firefox),
        'org.mozilla.firefox.Bookmarks':
            collectors['org.mozilla.firefox.Bookmarks'].get_changeset(firefoxbookmarks),
        'org.freedesktop.NetworkManager':
            collectors['org.freedesktop.NetworkManager'].get_changeset(networkmanager)
    };

    spinnerDialog.show(
        _('Saving settings to profile. Please wait...'),
        _('Saving settings')
    );

    $('#event-logs').modal('hide');

    stopLiveSession(function () {
        const uid = sessionStorage.getItem("fc.session.profile_uid");
        if (DEBUG > 0) {
            console.log('FC: Saving live session settings');
        }
        fc.SessionSave(uid, changesets, function (resp) {
            if (resp.status) {
                if (DEBUG > 0) {
                    console.log('FC: Saved live session settings');
                }
                location.href = 'index.html';
            } else {
                messageDialog.show(
                    _('Error saving session'),
                    _('Error')
                );
                spinnerDialog.close();
            }
        }, function () {
            console.log('FC: Error saving live session settings');
        });
    });
}

$(document).ready(function () {
    $('#reconnect-to-vm').click(reconnectToVM);
    $('#close-live-session').click(stopLiveSession);
    $('#review-changes').click(reviewAndSubmit);
    $('#deploy-profile').click(deployProfile);

    // Create a Fleet Commander dbus client instance
    fc = new FleetCommanderDbusClient(function () {
        fc.GetInitialValues(function (resp) {
            setDebugLevel(resp.debuglevel);

            // Try domain connection
            fc.DoDomainConnection(function (resp) {
                if (resp.status) {
                    $('#main-container').show();
                    startLiveSession();
                    // Error catchall to workarount "oops" message in cockpit
                    window.onerror = function (message, url, lineNumber) {
                        if (DEBUG > 0) {
                            console.error('Live session error: (', lineNumber, ' ', url, ') ', message);
                        }
                        return true;
                    };
                } else {
                    fc.Quit();
                    $('#main-container').hide();
                    console.log(resp.error);
                    showCurtain(
                        _('Error connecting to FC service. Check system logs for details'),
                        _('Error connecting to FC service'),
                        null,
                        {
                            'dbus-retry': {
                                text: 'Retry connection',
                                class: 'btn-primary',
                                callback: function () { location.reload() }
                            }
                        }
                    );
                }
            });
        });
    }, function () {
        $('#main-container').hide();
        showCurtain(
            _('Can not connect with Fleet Commander dbus service'),
            _('Can\'t connect to Fleet Commander'),
            null,
            {
                'dbus-retry': {
                    text: 'Retry connection',
                    class: 'btn-primary',
                    callback: function () { location.reload() }
                },
            }
        );
    });
});
