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

/*jslint browser: true */
/*jslint nomen: true */
/*global $ */
/*global cockpit */
/*global Uint8Array */
/*global arraybuffer_to_str_func */
/*global setDebugLevel */
/*global SpinnerDialog */
/*global MessageDialog */
/*global showCurtain */
/*global FleetCommanderDbusClient */
/*global FleetCommanderSpiceClient */
/*global BaseCollector */
/*global FirefoxBookmarksCollector */
/*global NMCollector */

"use strict";


var DEBUG = 0,
    _ = cockpit.gettext,
    fc = null,
    fcsc = null,
    spinnerDialog,
    messageDialog,
    heartbeat = null,
    collectors = {
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
    var data = '[virt-viewer]\n' +
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
    var msg_text = arraybuffer_to_str_func(new Uint8Array(data));
    console.log('FC: Parsing data', msg_text);
    try {
        var change = JSON.parse(msg_text);
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
            console.log('FC: Error while parsing change', msg_text);
        }
    }
}

function startSpiceHtml5(conn_details) {
    // SPICE port changes listeners
    window.addEventListener('spice-port-data', function (event) {
        if (event.detail.channel.portName === 'org.freedesktop.FleetCommander.0') {
            if (DEBUG > 0) {
                console.log(
                    'FC: Logger data received in spice port',
                    event.detail.channel.portName,
                );
            }
            ParseChange(event.detail.data);
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

    var details = {
        path: conn_details.path,
        ticket: conn_details.ticket,
    };

    fcsc = new FleetCommanderSpiceClient(
        details, function () {
            stopLiveSession()
        },
    );
    startHeartBeat();
}


function startRemoteViewer(conn_details) {
    var console_details = {
        type: 'spice',
        address: conn_details.host,
        tls_port: conn_details.tls_port,
        ca_cert: conn_details.ca_cert.replace(/\n/g, "\\n"),
        cert_subject: conn_details.cert_subject,
        ticket: conn_details.ticket,
    };
    downloadConnectionFile(console_details);

    var options = {
        payload: 'stream',
        protocol: 'binary',
        unix: conn_details.notify_socket,
        binary: true,
    };
    var channel = cockpit.channel(options);

    channel.addEventListener("ready", function(event, options) {
        if (DEBUG > 0) {
            console.log('FC: Cockpit changes channel is open');
        }
    });
    channel.addEventListener("message", function(event, data) {
        if (DEBUG > 0) {
            console.log('FC: Logger data received in unix channel', data);
        }
        ParseChange(data);
    });
    channel.addEventListener("close", function(event, options) {
        if (DEBUG > 0) {
            console.log('FC: Cockpit changes channel is closed', options);
        }
        stopLiveSession()
    });

    startHeartBeat();
}

function startHeartBeat() {
    heartbeat = window.setInterval(function () {
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


function startLiveSession() {
    spinnerDialog.show(
        _('Connecting to virtual machine')
    );
    // Stop any previous session
    stopLiveSession(function () {
        var domain = sessionStorage.getItem("fc.session.domain");
        fc.SessionStart(domain, function (resp) {
            if (resp.status) {
                var conn_details = resp.connection_details;
                var viewers = {
                    'spice_html5': startSpiceHtml5,
                    'spice_remote_viewer': startRemoteViewer,
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
    }
}


function addSectionCheckbox(section) {
    var section_header = $(section).prev("h4"),
        chkbox_container = $(
            '<div/>',
            {
                class: 'list-view-pf-checkbox',
                id: section.replace("#", "") + '-chkbox-container'
            }
        ),
        checkbox = $('<input/>', {type: 'checkbox'});

    checkbox.click(function () {
        var sectionChecked = this.checked;
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
    /*jslint unparam: true */
    $.each(data, function (unusedIndex, item) {
        var citem = $($('#change-item-template').html()),
            checkbox,
            row;

        if (only_value) {
            row = item[1];
        } else {
            row = item.join(" ");
        }

        citem.appendTo($(section));
        checkbox = citem.find('input[type=checkbox]');
        checkbox.attr('data-id', item[0]);
        citem.find('.changekey').html(row);
    });
    /*jslint unparam: false */
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
    populateSectionChanges('#libreoffice-event-list',
        collectors['org.libreoffice.registry'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating GSettings change list');
    }
    populateSectionChanges('#gsettings-event-list',
        collectors['org.gnome.gsettings'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating Chromium change list');
    }
    populateSectionChanges('#chromium-event-list',
        collectors['org.chromium.Policies'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating Chrome change list');
    }
    populateSectionChanges('#chrome-event-list',
        collectors['com.google.chrome.Policies'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating Firefox change list');
    }
    populateSectionChanges('#firefox-event-list',
        collectors['org.mozilla.firefox'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating Firefox bookmarks change list');
    }
    populateSectionChanges('#firefoxbookmarks-event-list',
        collectors['org.mozilla.firefox.Bookmarks'].dump_changes());

    if (DEBUG > 0) {
        console.log('FC: Populating NetworkManager change list');
    }
    populateSectionChanges('#networkmanager-event-list',
        collectors['org.freedesktop.NetworkManager'].dump_changes());
}


function reviewAndSubmit() {
    $('.change-checkbox').show();
    populateChanges();
    $('#event-logs').modal('show');
}


function deployProfile() {
    var gsettings = [],
        libreoffice = [],
        chromium = [],
        chrome = [],
        firefox = [],
        firefoxbookmarks = [],
        networkmanager = [],
        changesets;

    /*jslint unparam: true */
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
    /*jslint unparam: false */

    changesets = {
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
        var uid = sessionStorage.getItem("fc.session.profile_uid");
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

    spinnerDialog = new SpinnerDialog();
    messageDialog = new MessageDialog();

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
                                callback: function () { location.reload(); }
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
                    callback: function () { location.reload(); }
                },
            }
        );
    });
});
