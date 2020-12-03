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

import { messageDialog, questionDialog } from './dialogs.js';

const _ = cockpit.gettext;

class Goa {
    constructor() {
        this.current_goa_accounts = null;
        this.current_goa_account_id = null;
        this.GOA_PROVIDERS = null;
        this.currentprofile = null;

        this.sortNamedEntries = this.sortNamedEntries.bind(this);
        this.updateProviderServices = this.updateProviderServices.bind(this);
        this.showAccountEdit = this.showAccountEdit.bind(this);
        this.removeAccount = this.removeAccount.bind(this);
        this.addAccountItem = this.addAccountItem.bind(this);
        this.populateAccounts = this.populateAccounts.bind(this);
        this.showAccounts = this.showAccounts.bind(this);
        this.getAccountProviderServicesData = this.getAccountProviderServicesData.bind(this);
        this.updateOrAddAccount = this.updateOrAddAccount.bind(this);
        this.saveAccounts = this.saveAccounts.bind(this);
        this.initialize = this.initialize.bind(this);
    }

    sortNamedEntries(data) {
        const entries = [];
        $.each(data, (key, elem) => {
            entries.push([key, elem]);
        });
        entries.sort((a, b) => a[1].name.localeCompare(b[1].name));
        return entries;
    }

    updateProviderServices() {
        const provider = $('#goa-provider').val();
        const services = this.GOA_PROVIDERS[provider].services;
        const serviceblock = $('#goa-services');
        const entries = this.sortNamedEntries(services);

        $('#goa-current-provider-icon').attr('src', 'img/goa/' + provider + '.png');
        serviceblock.html('');

        $.each(entries, index => {
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

    showAccountEdit(account_id) {
        const combo = $('#goa-provider');
        const entries = this.sortNamedEntries(this.GOA_PROVIDERS);

        combo.html('');
        $.each(entries, index => {
            const key = entries[index][0];
            const elem = entries[index][1];

            if (key === 'google') {
                combo.append('<option value="' + key + '" selected>' + elem.name + '</option>');
            } else {
                combo.append('<option value="' + key + '">' + elem.name + '</option>');
            }
        });

        if (typeof account_id === 'string') {
            const account = this.current_goa_accounts[account_id];
            combo.val(account.Provider);
            this.updateProviderServices();
            // Set selected services
            $('#goa-services input[type=checkbox]').each(function() {
                const service = $(this).attr('data-service');
                $(this).prop('checked', account[service] === true);
            });
            this.current_goa_account_id = account_id;
        } else {
            this.updateProviderServices();
            this.current_goa_account_id = null;
        }
        $('#goa-accounts-modal').modal('hide');
        $('#goa-account-edit-modal').modal('show');
    }

    removeAccount(account_id) {
        questionDialog.show(
            _('Are you sure you want remove "' + account_id + '"?'),
            _('Remove GOA account confirmation'),
            () => {
                delete this.current_goa_accounts[account_id];
                questionDialog.close();
                this.populateAccounts();
            }
        );
    }

    addAccountItem(account_id, account_data) {
        const tr = $('<tr></tr>');
        const provider = $('<td></td>', {
            text: this.GOA_PROVIDERS[account_data.Provider].name
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
                .click(() => { this.showAccountEdit(account_id) })
                .appendTo(actions_container);

        $('<button></button>', { class: "btn btn-danger", text: _('Delete') })
                .click(() => { this.removeAccount(account_id) })
                .appendTo(actions_container);

        tr.appendTo('#goa-accounts-list');
    }

    populateAccounts() {
        $('#goa-accounts-list').html('');
        $.each(this.current_goa_accounts, (key, account) => {
            this.addAccountItem(key, account);
        });
    }

    showAccounts() {
        // Populate GOA accounts list
        this.populateAccounts();
        $('#profile-modal').modal('hide');
        $('#goa-accounts-modal').modal('show');
    }

    getAccountProviderServicesData() {
        const provider = $('#goa-provider').val();
        const data = { Provider: provider };
        $('#goa-services input[type=checkbox]').each(function() {
            const service = $(this).attr('data-service');
            const enabled = $(this).is(':checked');
            data[service] = enabled;
        });
        return data;
    }

    updateOrAddAccount() {
        const data = this.getAccountProviderServicesData();
        let repeated = false;
        let provider,
            account_id;
        $.each(this.current_goa_accounts, (account_id, account) => {
            if (account.Provider === data.Provider) {
                if (this.current_goa_account_id) {
                    if (this.current_goa_account_id !== account_id) {
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

        if (!this.current_goa_account_id) {
            while (true) {
                account_id = 'Template account_fc_' +
                    Math.floor(new Date() / 1000).toString() + '_0';
                if (!this.current_goa_accounts[account_id]) {
                    break;
                }
            }
        } else {
            account_id = this.current_goa_account_id;
        }
        this.current_goa_accounts[account_id] = data;
        this.populateAccounts();
        $('#goa-account-edit-modal').modal('hide');
    }

    saveAccounts() {
        const currentprofile = this.currentprofile();
        currentprofile.settings['org.gnome.online-accounts'] = this.current_goa_accounts;
        $('#goa-accounts-modal').modal('hide');
        $('#profile-modal').modal('show');
    }

    /*******************************************************************************
     * Initialization
     ******************************************************************************/
    initialize(resp, currentprofile_cb) {
        if (resp.status) {
            this.GOA_PROVIDERS = resp.providers;
            this.currentprofile = currentprofile_cb;

            // Bind GOA related events
            $('#show-goa-accounts').click(() => {
                const currentprofile = this.currentprofile();
                this.current_goa_accounts = currentprofile.settings['org.gnome.online-accounts'] || {};
                const typestring = Object.prototype.toString.call({});
                if (Object.prototype.toString.call(this.current_goa_accounts) !== typestring) {
                    this.current_goa_accounts = {};
                }
                this.showAccounts();
            });
            $('#show-goa-account-edit').click(this.showAccountEdit);
            $('#goa-provider').change(this.updateProviderServices);
            $('#update-add-goa-account').click(this.updateOrAddAccount);
            $('#save-goa-accounts').click(() => {
                this.saveAccounts();
            });

            $('#goa-accounts-modal').keypress(e => {
                const code = e.keyCode || e.which;
                if (code === 13) {
                    this.saveAccounts();
                }
            });

            $('#goa-account-edit-modal').keypress(e => {
                const code = e.keyCode || e.which;
                if (code === 13) {
                    this.updateOrAddAccount();
                }
            });

            $('#goa-account-edit-modal').on('hide.bs.modal', () => {
                this.showAccounts();
            });
        } else {
            messageDialog.show(
                _('Error loading GOA providers. GOA support will not be available'),
                _('Error')
            );
            $('#show-goa-accounts').hide();
        }
    }
}

const goa = new Goa();

export { goa };
