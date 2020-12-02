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

import { MessageDialog, QuestionDialog } from './dialogs.js';

const _ = cockpit.gettext;
const messageDialog = new MessageDialog();
const questionDialog = new QuestionDialog();

let current_goa_accounts = null;
let current_goa_account_id = null;
let GOA_PROVIDERS = null;

function sortGoaNamedEntries(data) {
    const entries = [];
    $.each(data, function (key, elem) {
        entries.push([key, elem]);
    });
    entries.sort(function (a, b) {
        return a[1].name.localeCompare(b[1].name);
    });
    return entries;
}

function updateProviderServices() {
    const provider = $('#goa-provider').val();
    const services = GOA_PROVIDERS[provider].services;
    const serviceblock = $('#goa-services');
    const entries = sortGoaNamedEntries(services);

    $('#goa-current-provider-icon').attr('src', 'img/goa/' + provider + '.png');
    serviceblock.html('');

    $.each(entries, function (index) {
        const key = entries[index][0];
        const elem = entries[index][1];
        if (elem.enabled) {
            serviceblock.append('<div class="checkbox"><label>' +
                '<input type="checkbox" ' +
                'id="goa-service-' + key + '" ' +
                'name="goa-service-' + key + '" ' +
                'data-service="' + key + '" /> ' +
                '<span>' + services[key].name + '</span></label></div>');
        }
    });
}

function showGOAAccountEdit(account_id) {
    const combo = $('#goa-provider');
    const entries = sortGoaNamedEntries(GOA_PROVIDERS);

    combo.html('');
    $.each(entries, function (index) {
        const key = entries[index][0];
        const elem = entries[index][1];

        if (key === 'google') {
            combo.append('<option value="' + key + '" selected>' + elem.name + '</option>');
        } else {
            combo.append('<option value="' + key + '">' + elem.name + '</option>');
        }
    });

    if (typeof account_id === 'string') {
        const account = current_goa_accounts[account_id];
        combo.val(account.Provider);
        updateProviderServices();
        // Set selected services
        $('#goa-services input[type=checkbox]').each(function () {
            const service = $(this).attr('data-service');
            $(this).prop('checked', account[service] === true);
        });
        current_goa_account_id = account_id;
    } else {
        updateProviderServices();
        current_goa_account_id = null;
    }
    $('#goa-accounts-modal').modal('hide');
    $('#goa-account-edit-modal').modal('show');
}

function removeGOAAccount(account_id) {
    questionDialog.show(
        _('Are you sure you want remove "' + account_id + '"?'),
        _('Remove GOA account confirmation'),
        function () {
            delete current_goa_accounts[account_id];
            questionDialog.close();
            populateGOAAccounts();
        }
    );
}

function addGOAAccountItem(account_id, account_data) {
    const tr = $('<tr></tr>');
    const provider = $('<td></td>', {
        text: GOA_PROVIDERS[account_data.Provider].name
    });
    const p_icon = $('<img class="goa-provider-icon" src="img/goa/' +
        account_data.Provider + '.png">');
    const actions_col = $('<td></td>');
    const actions_container = $('<span></span>', { class: 'pull-right' });

    $('<td></td>', { text: account_id }).appendTo(tr);
    p_icon.prependTo(provider);
    provider.appendTo(tr);
    actions_col.appendTo(tr);
    actions_container.appendTo(actions_col);

    $('<button></button>', { class: "btn btn-default", text: _('Edit') })
            .click(function () { showGOAAccountEdit(account_id) })
            .appendTo(actions_container);

    $('<button></button>', { class: "btn btn-danger", text: _('Delete') })
            .click(function () { removeGOAAccount(account_id) })
            .appendTo(actions_container);

    tr.appendTo('#goa-accounts-list');
}

function populateGOAAccounts() {
    $('#goa-accounts-list').html('');
    $.each(current_goa_accounts, function (key, account) {
        addGOAAccountItem(key, account);
    });
}

function showGOAAccounts() {
    // Populate GOA accounts list
    populateGOAAccounts();
    $('#profile-modal').modal('hide');
    $('#goa-accounts-modal').modal('show');
}

function getAccountProviderServicesData() {
    const provider = $('#goa-provider').val();
    const data = { Provider: provider };
    $('#goa-services input[type=checkbox]').each(function () {
        const service = $(this).attr('data-service');
        const enabled = $(this).is(':checked');
        data[service] = enabled;
    });
    return data;
}

function updateOrAddGOAAccount() {
    const data = getAccountProviderServicesData();
    let repeated = false;
    let provider,
        account_id;
    $.each(current_goa_accounts, function (account_id, account) {
        if (account.Provider === data.Provider) {
            if (current_goa_account_id) {
                if (current_goa_account_id !== account_id) {
                    repeated = true;
                }
            } else {
                repeated = true;
                provider = account.Provider;
            }
        }
    });

    if (repeated) {
        messageDialog.show(
            _('There exists another account for provider ') + provider,
            _('Error')
        );
        return;
    }

    if (!current_goa_account_id) {
        while (true) {
            account_id = 'Template account_fc_' +
                Math.floor(new Date() / 1000).toString() + '_0';
            if (!current_goa_accounts[account_id]) {
                break;
            }
        }
    } else {
        account_id = current_goa_account_id;
    }
    current_goa_accounts[account_id] = data;
    populateGOAAccounts();
    $('#goa-account-edit-modal').modal('hide');
}

function saveGOAAccounts(currentprofile) {
    currentprofile.settings['org.gnome.online-accounts'] = current_goa_accounts;
    $('#goa-accounts-modal').modal('hide');
    $('#profile-modal').modal('show');
}

/*******************************************************************************
 * Initialization
 ******************************************************************************/
function initialize_goa(currentprofile, resp) {
    if (resp.status) {
        GOA_PROVIDERS = resp.providers;
        // Bind GOA related events
        $('#show-goa-accounts').click(function () {
            current_goa_accounts = currentprofile.settings['org.gnome.online-accounts'] || {};
            const typestring = Object.prototype.toString.call({});
            if (Object.prototype.toString.call(current_goa_accounts) !== typestring) {
                current_goa_accounts = {};
            }
            showGOAAccounts();
        });
        $('#show-goa-account-edit').click(showGOAAccountEdit);
        $('#goa-provider').change(updateProviderServices);
        $('#update-add-goa-account').click(updateOrAddGOAAccount);
        $('#save-goa-accounts').click(() => {
            saveGOAAccounts(currentprofile);
        });

        $('#goa-accounts-modal').keypress(function (e) {
            const code = e.keyCode || e.which;
            if (code === 13) {
                saveGOAAccounts(currentprofile);
            }
        });

        $('#goa-account-edit-modal').keypress(function (e) {
            const code = e.keyCode || e.which;
            if (code === 13) {
                updateOrAddGOAAccount();
            }
        });

        $('#goa-account-edit-modal').on('hide.bs.modal', function () {
            showGOAAccounts();
        });
    } else {
        messageDialog.show(
            _('Error loading GOA providers. GOA support will not be available'),
            _('Error')
        );
        $('#show-goa-accounts').hide();
    }
}

export { initialize_goa };
