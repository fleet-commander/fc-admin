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

var current_goa_accounts = null;
var current_goa_account_id = null;

function showGOAAccounts() {
  // Populate GOA accounts list
  populateGOAAccounts();
  $('#edit-profile-modal').modal('hide');
  $('#goa-accounts-modal').modal('show');
}

function getGOAAccount(account_id) {
  var account;
  $.each(current_goa_accounts, function(index, element) {
    if (element[account_id]) account = element[account_id];
  });
  return account;
}

function getGOAAccountId(account) {
  var account_id = null;
  $.each(account, function(key, value) {
    if (/^Account account_/.test(key)) {
      account_id = key;
    }
  })
  return account_id
}

function populateGOAAccounts() {
  $('#goa-accounts-list').html('')
  $(current_goa_accounts).each(function(){
    addGOAAccountItem(this);
  })
}

function addGOAAccountItem(val) {
  var account_id = getGOAAccountId(val);
  if (!account_id) return

  var account_data = val[account_id]

  var tr = $('<tr></tr>');
  $('<td></td>', { text: account_id }).appendTo(tr);
  var provider = $('<td></td>', { text: account_data.Provider });
  p_icon = $('<img class="goa-provider-icon" src="img/goa/' +
    account_data.Provider + '.png">')
  p_icon.prependTo(provider)
  provider.appendTo(tr);

  var actions_col = $('<td></td>');
  actions_col.appendTo(tr);

  var actions_container = $('<span></span>', { class: 'pull-right' });
  actions_container.appendTo(actions_col)

  $('<button></button>', {"class": "btn btn-default", text: _('Edit')})
    .click(function () { showGOAAccountEdit(account_id); })
    .appendTo(actions_container);

  $('<button></button>', {"class": "btn btn-danger", text: _('Delete')})
    .click(function () { removeGOAAccount (account_id); })
    .appendTo(actions_container);

  tr.appendTo('#goa-accounts-list');
}

function showGOAAccountEdit(account_id) {
  combo = $('#goa-provider');
  combo.html('');
  $.each(GOA_PROVIDERS, function(key, element) {
    combo.append('<option value="' + key + '">' + element.name + '</option>')
  });

  if (typeof(account_id) == 'string') {
    var account = getGOAAccount(account_id);
    combo.val(account.Provider);
    updateProviderServices();
    // Set selected services
    $('#goa-services input[type=checkbox]').each(function(){
      service = $(this).attr('data-service')
      $(this).prop('checked', account[service] == true);
    })
    current_goa_account_id = account_id;
  } else {
    updateProviderServices();
    current_goa_account_id = null;
  }
  $('#goa-accounts-modal').modal('hide');
  $('#goa-account-edit-modal').modal('show');

}

function removeGOAAccount(account_id, no_ask, replace) {
  function remove() {
    var remove_index = null;
    $.each(current_goa_accounts, function(index, element) {
      if (element[account_id]) remove_index = index;
    });
    if (remove_index != null) {
      if (replace) {
        current_goa_accounts.splice(remove_index, 1, replace);
      } else {
        current_goa_accounts.splice(remove_index, 1);
      }
    }
    populateGOAAccounts();
  }

  if (no_ask) {
    remove();
  } else {
    showQuestionDialog(
      _('Do you want remove this account?'),
      _('Remove GOA account'),function() {
        remove()
        $('#message-dialog-modal').modal('hide');
      });
  }
}

function updateProviderServices() {
  var provider = $('#goa-provider').val();
  $('#goa-current-provider-icon').attr('src', 'img/goa/' + provider + '.png');
  var services = GOA_PROVIDERS[provider].services;
  var serviceblock = $('#goa-services');
  serviceblock.html('');
  $.each(services, function(key, element) {
    if (services[key].enabled) {
      service = '<div class="checkbox"><label>' +
        '<input type="checkbox" ' +
          'id="goa-service-' + key + '" ' +
          'name="goa-service-' + key + '" ' +
          'data-service="' + key + '" /> ' +
        '<span>' + services[key].name + '</span></label></div>';
      serviceblock.append(service);
    }
  });
}

function updateOrAddGOAAccount() {
  data = getAccountProviderServicesData();
  // Check for repeated accounts
  var repeated = false;
  $.each(current_goa_accounts, function(index, elem) {
    var cur_account_id = getGOAAccountId(elem);
    var account = elem[cur_account_id];
    if (account.Provider == data.Provider) {
      if (current_goa_account_id) {
        if (current_goa_account_id != cur_account_id)
          repeated = true;
      } else {
        repeated = true;
      }
    }
  });

  if (repeated) {
    showMessageDialog(
      _('There exists another account for provider ') + provider,
      _('Error'))
      return
  }

  var account_data = {};
  if (!current_goa_account_id) {
    var account_id;
    while (true) {
      account_id = 'Account account_fc_' +
                    Math.floor(new Date() / 1000).toString() + '_0';
      if (!getGOAAccount(account_id)) break;
    }
    account_data[account_id] = data;
    current_goa_accounts.push(account_data)
    populateGOAAccounts();
  } else {
    account_data[current_goa_account_id] = data;
    removeGOAAccount(current_goa_account_id, true, account_data);
  }
  $('#goa-account-edit-modal').modal('hide');
}

function getAccountProviderServicesData() {
  provider = $('#goa-provider').val()
  data = { Provider: provider }
  $('#goa-services input[type=checkbox]').each(function(elem){
    service = $(this).attr('data-service')
    enabled = $(this).is(':checked')
    data[service] = enabled
  })
  return data
}

function saveGOAAccounts() {
  fc.GOAAccounts(current_goa_accounts, currentuid, function(resp) {
    if (resp.status) {
      currentprofile['settings']['org.gnome.online-accounts'] =
        current_goa_accounts
      $('#goa-accounts-modal').modal('hide');
      $('#edit-profile-modal').modal('show');
    } else {
      showMessageDialog(
        _('There has been an error saving GNOME online accounts'), _('Error'))
    }
  });
}

/*******************************************************************************
 * Initialization
 ******************************************************************************/
$(document).ready (function () {
  fc.GetGOAProviders(function(resp){
    if(resp.status) {
      GOA_PROVIDERS = resp.providers;
      // Bind GOA related events
      $('#show-goa-accounts').click(function () {
        current_goa_accounts =
          currentprofile['settings']['org.gnome.online-accounts'] || [];
        var typestring = Object.prototype.toString.call(current_goa_accounts);
        if (typestring != '[Object array]')
          current_goa_accounts = []
        showGOAAccounts();
      });
      $('#show-goa-account-edit').click(showGOAAccountEdit);
      $('#goa-provider').change(updateProviderServices);
      $('#update-add-goa-account').click(updateOrAddGOAAccount);
      $('#save-goa-accounts').click(saveGOAAccounts);

      $('#goa-account-edit-modal').on('hide.bs.modal', function () {
        showGOAAccounts(current_goa_accounts);
      });
    } else {
      showMessageDialog(
        _('Error loading GOA providers. GOA support will not be available'),
        _('Error'))
        $('#show-goa-accounts').hide();
    }
  });
});
