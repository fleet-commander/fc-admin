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

const _ = cockpit.gettext;

var current_goa_accounts = null;
var current_goa_account_id = null;
var GOA_PROVIDERS = null;

function sortGoaNamedEntries(data) {
    var entries = [];
    $.each(data, function (key, elem) {
        entries.push([key, elem]);
    });
    entries.sort(function (a, b) {
        return a[1].name.localeCompare(b[1].name);
    });
    return entries;
}

function updateProviderServices() {
    var provider = $('#goa-provider').val();
    var services = GOA_PROVIDERS[provider].services;
    var serviceblock = $('#goa-services');
    var entries = sortGoaNamedEntries(services);

    $('#goa-current-provider-icon').attr('src', 'img/goa/' + provider + '.png');
    serviceblock.html('');

    $.each(entries, function (index) {
        var key = entries[index][0];
        var elem = entries[index][1];
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
    var combo = $('#goa-provider');
    var entries = sortGoaNamedEntries(GOA_PROVIDERS);
    var account;

    combo.html('');
    $.each(entries, function (index) {
        var key = entries[index][0];
        var elem = entries[index][1];

        if (key === 'google') {
            combo.append('<option value="' + key + '" selected>' + elem.name + '</option>');
        } else {
            combo.append('<option value="' + key + '">' + elem.name + '</option>');
        }
    });

    if (typeof account_id === 'string') {
        account = current_goa_accounts[account_id];
        combo.val(account.Provider);
        updateProviderServices();
        // Set selected services
        $('#goa-services input[type=checkbox]').each(function () {
            var service = $(this).attr('data-service');
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

// Dirty workaround to avoid jslint error on cyclic calls
var populateGOAAccounts;

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
    var tr = $('<tr></tr>');
    var provider = $('<td></td>', {
        text: GOA_PROVIDERS[account_data.Provider].name
    });
    var p_icon = $('<img class="goa-provider-icon" src="img/goa/' +
        account_data.Provider + '.png">');
    var actions_col = $('<td></td>');
    var actions_container = $('<span></span>', { class: 'pull-right' });

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

// Part 2 of dirty workaround to avoid jslint error on cyclic calls
populateGOAAccounts = function () {
    $('#goa-accounts-list').html('');
    $.each(current_goa_accounts, function (key, account) {
        addGOAAccountItem(key, account);
    });
};

function showGOAAccounts() {
    // Populate GOA accounts list
    populateGOAAccounts();
    $('#profile-modal').modal('hide');
    $('#goa-accounts-modal').modal('show');
}

function getAccountProviderServicesData() {
    var provider = $('#goa-provider').val();
    var data = { Provider: provider };
    $('#goa-services input[type=checkbox]').each(function () {
        var service = $(this).attr('data-service');
        var enabled = $(this).is(':checked');
        data[service] = enabled;
    });
    return data;
}

function updateOrAddGOAAccount() {
    var data = getAccountProviderServicesData();
    var repeated = false;
    var provider,
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

function saveGOAAccounts() {
    currentprofile.settings['org.gnome.online-accounts'] = current_goa_accounts;
    $('#goa-accounts-modal').modal('hide');
    $('#profile-modal').modal('show');
}

/*******************************************************************************
 * Initialization
 ******************************************************************************/
function initialize_goa(fc) {
    fc.GetGOAProviders(function (resp) {
        if (resp.status) {
            GOA_PROVIDERS = resp.providers;
            // Bind GOA related events
            $('#show-goa-accounts').click(function () {
                current_goa_accounts = currentprofile.settings['org.gnome.online-accounts'] || {};
                var typestring = Object.prototype.toString.call({});
                if (Object.prototype.toString.call(current_goa_accounts) !== typestring) {
                    current_goa_accounts = {};
                }
                showGOAAccounts();
            });
            $('#show-goa-account-edit').click(showGOAAccountEdit);
            $('#goa-provider').change(updateProviderServices);
            $('#update-add-goa-account').click(updateOrAddGOAAccount);
            $('#save-goa-accounts').click(saveGOAAccounts);

            $('#goa-accounts-modal').keypress(function (e) {
                var code = e.keyCode || e.which;
                if (code === 13) {
                    saveGOAAccounts();
                }
            });

            $('#goa-account-edit-modal').keypress(function (e) {
                var code = e.keyCode || e.which;
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
    });
}

export { initialize_goa };
