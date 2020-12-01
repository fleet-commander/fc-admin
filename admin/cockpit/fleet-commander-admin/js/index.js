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

import {
    DEBUG,
    addFormError,
    clearModalFormErrors,
    setDebugLevel
} from './base.js';
import {
    SpinnerDialog,
    QuestionDialog,
    MessageDialog,
    showCurtain
} from './dialogs.js';
import { FleetCommanderDbusClient } from './fcdbusclient.js';
import { initialize_goa } from './goa.js';
import {
    addHighlightedAppFromEntry,
    saveHighlightedApps,
    showHighlightedApps
} from './highlightedapps.js';

const _ = cockpit.gettext;

var fc = null;
var currentuid = null;
var currentprofile = null;
var state = {
    debuglevel: 'info',
    defaults: {
        profilepriority : 50
    }
};
var spinnerDialog = null;
var questionDialog = null;
var messageDialog = null;

/*******************************************************************************
 * Application configuration
 ******************************************************************************/

function showFCSettings() {
    fc.GetHypervisorConfig(function (resp) {
        clearModalFormErrors('fc-settings-modal');
        $('#host').val(resp.host);
        $('#username').val(resp.username);
        $('#mode option[value="' + resp.mode + '"]').prop('selected', true);
        $('#viewer option[value="' + resp.viewer + '"]').prop('selected', true);
        $('#pubkey').html(resp.pubkey);
        fc.GetGlobalPolicy(function (resp) {
            if (resp.status) {
                $('#policy').val(resp.policy);
            } else {
                messageDialog.show(
                    _('Error getting global policy'),
                    _('Error')
                );
            }
        });
        $('#fc-settings-modal').modal('show');
    });
}

function checkHypervisorConfig(cb) {
    // Show hypervisor dialog if not configured
    fc.GetHypervisorConfig(function (data) {
        if (data.needcfg) {
            showFCSettings();
        } else {
            if (cb) {
                cb(data);
            }
        }
    });
}

function addToKnownHosts(hostname, cb, data) {
    fc.AddKnownHost(hostname, function (resp) {
        if (resp.status) {
            cb(data);
        } else {
            messageDialog.show(resp.error, _('Error'));
        }
    });
}

function checkKnownHost(hostname, cb, data) {
    data = data || {};
    fc.CheckKnownHost(hostname, function (resp) {
        if (resp.status) {
            cb(data);
        } else if (resp.error !== undefined) {
            // We have an error
            messageDialog.show(resp.error, _('Error'));
        } else if (resp.fprint !== undefined) {
            questionDialog.show(
                _('Do you want to add this host to known hosts?') +
                    '<p>' + _('Fingerprint data') + ':</p>' +
                    '<p>' + resp.fprint + '</p>',
                _('Hypervisor host verification'),
                function () {
                    // Add host to known hosts
                    questionDialog.close();
                    addToKnownHosts(hostname, cb, data);
                }
            );
        }
    });
}

function saveFCSettings(cb) {
    if (DEBUG > 0) {
        console.log('FC: Saving hypervisor configuration');
    }

    clearModalFormErrors('fc-settings-modal');

    var data = {
        host: $('#host').val(),
        username: $('#username').val(),
        mode: $('#mode').val(),
        viewer: $('#viewer').val(),
        domains: {}
    };
    var policy = parseInt($('#policy').val(), 10);

    function saveSettingsFinal(data) {
        fc.SetHypervisorConfig(data, function (resp) {
            if (resp.status) {
                fc.SetGlobalPolicy(policy, function (resp) {
                    if (!resp.status) {
                        messageDialog.show(
                            _('Error setting global policy'),
                            _('Error')
                        );
                    }
                    $('#fc-settings-modal').modal('hide');
                    if (typeof cb === 'function') {
                        cb();
                    }
                });
            } else {
                messageDialog.show(resp.error, _('Error'));
            }
        });
    }

    fc.CheckHypervisorConfig(data, function (resp) {
        if (resp.status) {
            checkKnownHost(data.host, saveSettingsFinal, data);
        } else {
            $.each(resp.errors, function (key, value) {
                addFormError(key, value);
            });
        }
    });
}

function showPubkeyInstall() {
    saveFCSettings(function () {
        $('#pubkey-install-password').val('');
        $('#fc-settings-modal').modal('hide');
        $('#pubkey-install-modal').modal('show');
    });
}

function cancelPubkeyInstall() {
    messageDialog.close();
    $('#pubkey-install-modal').modal('hide');
    $('#fc-settings-modal').modal('show');
}

function installPubkey() {
    if (DEBUG > 0) {
        console.log('FC: Install public key');
    }

    $('#pubkey-install-modal').modal('hide');
    var host = $('#host').val();
    var user = $('#username').val();
    var pass = $('#pubkey-install-password').val();

    $('#pubkey-install-password').val('');

    spinnerDialog.show(
        _('Fleet Commander is installing the public key. Please wait'),
        _('Installing public key')
    );

    fc.InstallPubkey(host, user, pass, function (resp) {
        if (DEBUG > 0) {
            console.log('FC: Calling dbus for public key install');
        }

        spinnerDialog.close();

        if (resp.status) {
            messageDialog.show(
                _('Public key has been installed succesfuly'),
                _('Public key installed'),
                cancelPubkeyInstall
            );
        } else {
            messageDialog.show(resp.error, _('Error'), cancelPubkeyInstall);
        }
    });
}

function copyPubkeyToClipboard() {
    $('#pubkey').select();
    document.execCommand('copy');
    if (window.getSelection) {
        if (window.getSelection().empty) {
            window.getSelection().empty();
        } else if (window.getSelection().removeAllRanges) {
            window.getSelection().removeAllRanges();
        }
    } else if (document.selection) {
        document.selection.empty();
    }
}

/*******************************************************************************
 * Profiles
 ******************************************************************************/

function editProfile(uid) {
    fc.GetProfile(uid, function (resp) {
        if (resp.status) {
            currentuid = uid;
            currentprofile = resp.data;
            $('#profile-name').val(resp.data.name);
            $('#profile-desc').val(resp.data.description || '');
            $('#profile-priority').val(resp.data.priority || '');
            $('#profile-users').val(resp.data.users || '');
            $('#profile-groups').val(resp.data.groups || '');
            $('#profile-hosts').val(resp.data.hosts || '');
            $('#profile-hostgroups').val(resp.data.hostgroups || '');
            // Dhow settings adding buttons
            $('#edit-profile-further-group').show();
            // Show profile modal dialog
            $('#profile-modal').modal('show');
        } else {
            messageDialog.show(_('Error getting profile data'), _('Error'));
        }
    });
}

// Dirty workaround to avoid jslint error on cyclic calls
var removeProfile;

function refreshProfileList(cb) {
    // Populate profiles list
    fc.GetProfiles(function (resp) {
        if (resp.status) {
            var data = resp.data;
            // Clear profile list HTML
            $('#profile-list').html('');
            // Populate profile list
            /* jslint unparam: true */
            $.each(data, function (ignoreIndex, val) {
                var tr = $('<tr ></tr>');
                var actions_col = $('<td></td>');
                var actions_container = $(
                    '<span></span>',
                    { class: 'pull-right' }
                );
                var uid = val[0];

                $('<td></td>', { text: val[1] }).appendTo(tr);
                $('<td></td>', { text: val[2] }).appendTo(tr);
                actions_col.appendTo(tr);
                actions_container.appendTo(actions_col);

                $('<button></button>', {"class": "btn btn-default", text: _('Edit')})
                        .click(function () { editProfile(uid) })
                        .appendTo(actions_container);

                $('<button></button>', {"class": "btn btn-danger", text: _('Delete')})
                        .click(function () { removeProfile(uid, val[1]) })
                        .appendTo(actions_container);

                tr.appendTo('#profile-list');
            });
            /* jslint unparam: false */
        } else {
            messageDialog.show(resp.error, 'Error');
        }

        if (cb && typeof cb === 'function') {
            cb();
        }
    });
}

// Part 2 of dirty workaround to avoid jslint error on cyclic calls
removeProfile = function (uid, displayName) {
    questionDialog.show(
        _('Are you sure you want to delete profile') + ' "' + displayName + '"?',
        _('Delete profile confirmation'),
        function () {
            fc.DeleteProfile(uid, function () {
                refreshProfileList();
                questionDialog.close();
            });
        }
    );
};

function showAddProfile() {
    // Clear current profile
    currentprofile = null;
    currentuid = null;
    // Clear form data before show
    $('#profile-name').val('');
    $('#profile-desc').val('');
    $('#profile-priority').val(state.defaults.profilepriority);
    $('#profile-users').val('');
    $('#profile-groups').val('');
    $('#profile-hosts').val('');
    $('#profile-hostgroups').val('');
    // Hide settings adding buttons
    $('#edit-profile-further-group').hide();
    // Show profile modal dialog
    $('#profile-modal').modal('show');
}

function saveProfile() {
    clearModalFormErrors('profile-modal');

    if (!$('#profile-name').val()) {
        addFormError('profile-name', _('Profile name is required'));
        return;
    }

    if (!$('#profile-priority').val()) {
        addFormError('profile-priority', _('Priority is required'));
        return;
    }

    if (currentuid === null) {
        currentuid = $('#profile-name').val();
    }

    var data = {
        'cn': currentuid,
        'name': $('#profile-name').val(),
        'description': $('#profile-desc').val(),
        'priority': $('#profile-priority').val(),
        'users': $('#profile-users').val(),
        'groups': $('#profile-groups').val(),
        'hosts': $('#profile-hosts').val(),
        'hostgroups': $('#profile-hostgroups').val(),
    };

    if (currentprofile) {
        if (currentprofile.settings) {
            data.settings = currentprofile.settings;
        }
        // Check if profile is being renamed to add an 'oldname' field to data sent
        if (currentprofile.name && currentprofile.name !== data.name) {
            data.oldname = currentprofile.name;
        }
    } else {
        data.settings = {};
    }

    $('#profile-modal').modal('hide');
    spinnerDialog.show(_('Saving profile'));

    fc.SaveProfile(data, function (resp) {
        spinnerDialog.close();
        if (resp.status) {
            // Refresh profiles
            refreshProfileList();
        } else {
            messageDialog.show(
                _('Error saving profile') + ': ' + resp.error,
                _('Error')
            );
            $('#profile-modal').modal('show');
        }
    });
}

/*******************************************************************************
 * Live session management
 ******************************************************************************/

function selectDomain() {
    // Once selected the domain, set it's uuid in sessionStorage and redirect
    $('#domain-selection-modal').modal('hide');
    sessionStorage.setItem("fc.session.domain", $(this).attr('data-uuid'));
    sessionStorage.setItem("fc.session.profile_uid", currentuid);
    spinnerDialog.show(
        _('Starting live session. Please wait...')
    );
    setTimeout(function () {
        location.href = "livesession.html";
    }, 500);
}

function showDomainSelection() {
    checkHypervisorConfig(function (data) {
        checkKnownHost(data.host, function () {
            $('#profile-modal').modal('hide');
            $('#domain-selection-modal').modal('show');

            // Show loading clock
            var spinner = $('#domain-selection-modal .spinner');
            var list = $('#domain-selection-list');
            spinner.show();

            // Generate domain list
            list.html('');

            fc.ListDomains(function (resp) {
                if (resp.status) {
                    $('#domain-selection-modal .spinner').hide();
                    $.each(resp.domains, function () {
                        if (!this.temporary) {
                            var wrapper = $(
                                '<div></div>',
                                {'class': 'list-group-item'}
                            );
                            var text = this.name;
                            var domain = "";
                            if (!this.active) {
                                domain = $('<a></a>', { text: text, href: '#', 'data-uuid': this.uuid});
                                domain.click(selectDomain);
                            } else {
                                wrapper.addClass('grayed');
                                text = this.name + ' (' + _('running') + ')';
                                domain = $('<span></span>', { text: text, 'data-uuid': this.uuid});
                            }
                            domain.appendTo(wrapper);
                            wrapper.appendTo(list);
                        }
                    });

                    // If list is empty, show a message to inform user
                    if (list.html() === '') {
                        var wrapper = $(
                            '<div></div>',
                            {'class': 'list-group-item'}
                        );
                        var text = $(
                            '<span>No template virtual machines found</span>'
                        );
                        text.appendTo(wrapper);
                        wrapper.appendTo(list);
                    }
                } else {
                    $('#domain-selection-modal').modal('hide');
                    messageDialog.show(
                        _('Error getting domain list'),
                        _('Error')
                    );
                }
            });
        });
    });
}

/*******************************************************************************
 * Initialization
 ******************************************************************************/
$(document).ready(function () {
    // Bind events
    $('#show-fc-settings').click(showFCSettings);
    $('#save-fc-settings').click(saveFCSettings);
    $('#show-add-profile').click(showAddProfile);
    $('#save-new-profile').click(saveProfile);
    $('#show-highlighted-apps').click(showHighlightedApps);
    $('#add-highlighted-app').click(addHighlightedAppFromEntry);
    $('#save-highlighted-apps').click(saveHighlightedApps);
    $('#show-domain-selection').click(showDomainSelection);
    $('#show-pubkey-install').click(showPubkeyInstall);
    $('#cancel-pubkey-install').click(cancelPubkeyInstall);
    $('#install-pubkey').click(installPubkey);
    $('#copy-pubkey-to-clipboard').click(copyPubkeyToClipboard);

    $('#pubkey-install-password').keypress(function (e) {
        var code = e.keyCode || e.which;
        if (code === 13) {
            installPubkey();
        }
    });

    $('#profile-modal').keypress(function (e) {
        var code = e.keyCode || e.which;
        if (code === 13) {
            saveProfile();
        }
    });

    $('#fc-settings-modal').keypress(function (e) {
        var code = e.keyCode || e.which;
        if (code === 13) {
            saveFCSettings();
        }
    });

    $('#add-highlighted-app').keypress(function (e) {
        var code = e.keyCode || e.which;
        if (code === 13) {
            e.preventDefault();
        }
    });

    $('#highlighted-apps-modal').keypress(function (e) {
        var code = e.keyCode || e.which;
        if (code === 13) {
            saveHighlightedApps();
        }
    });

    $("#fc-settings-modal").on('shown.bs.modal', function () {
        $('#host').focus();
    });

    $("#profile-modal").on('shown.bs.modal', function () {
        $('#profile-name').focus();
    });

    $("#pubkey-install-modal").on('shown.bs.modal', function () {
        $('#pubkey-install-password').focus();
    });

    $("#highlighted-apps-modal").on('shown.bs.modal', function () {
        $('#app-name').focus();
    });

    spinnerDialog = new SpinnerDialog();
    questionDialog = new QuestionDialog();
    messageDialog = new MessageDialog();

    showCurtain(
        _('Fleet commander is initializing needed data. This action can last for some time depending on your system configuration. Please, be patient.'),
        _('Connecting to Fleet Commander service. Please wait...'),
        'spinner'
    );

    // Create a Fleet Commander dbus client instance
    fc = new FleetCommanderDbusClient(function () {
        fc.GetInitialValues(function (resp) {
            state.debuglevel = resp.debuglevel;
            state.defaults = resp.defaults;
            state.realm = resp.realm;
            state.server_type = resp.server_type;

            // Hide hostgroups if server type is Active Directory
            if (state.server_type === 'active-directory') {
                $('#profile-hostgroups-group').hide();
            }

            setDebugLevel(resp.debuglevel);

            // Try domain connection
            fc.DoDomainConnection(function (resp) {
                if (resp.status) {
                    checkHypervisorConfig();
                    initialize_goa(fc);
                    refreshProfileList(function () {
                        $('#main-container').show();
                        $('#curtain').hide();
                    });
                } else {
                    fc.Quit();
                    $('#main-container').hide();
                    console.log(resp.error);
                    showCurtain(
                        _('Error connecting to domain server. Check system logs for details'),
                        _('Error connecting to domain server'),
                        null,
                        {
                            'dbus-retry': {
                                text: 'Retry connection',
                                class: 'btn-primary',
                                callback: function () { location.reload() }
                            },
                        }
                    );
                }
            });
        });
    }, function (err) {
        $('#main-container').hide();
        console.log(err);
        showCurtain(
            _('Error during service connection. Check system logs for details'),
            _('Can\'t initialize Fleet Commander'),
            null,
            {
                'dbus-retry': {
                    text: 'Retry connection',
                    class: 'btn-primary',
                    callback: function () {
                        location.reload();
                    }
                },
            }
        );
    });
});
