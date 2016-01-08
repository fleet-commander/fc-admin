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

function showMessageDialog(message, title) {
  title = title || 'Info';
  var dialog = $('#message-dialog-modal');
  $('#message-dialog-modal h4').html(title);
  $('#message-dialog-modal .modal-body').html(message);
  dialog.modal('show');
}

function clearModalFormErrors(modalId) {
  $('#' + modalId + ' div.form-group').removeClass('has-error');
  $('#' + modalId + ' div.form-group > .error-message').remove();
}

function addFormError(fieldId, errorMessage) {
  $('#' + fieldId + '-group').append('<div class="help-block error-message">' + errorMessage + '</div>')
  $('#' + fieldId + '-group').addClass('has-error');
}

function populateProfileList() {
  $.ajaxSetup({cache: false});
  $.getJSON ("/profiles/", function (data) {
    $("#profile-list").html ("");
    $.each (data, function (i, val) {
      var tr = $('<tr ></tr>');
      $('<td></td>', { text: val.displayName }).appendTo(tr);
      $('<td></td>').appendTo(tr); // description
      $('<td></td>').appendTo(tr); // os
      $('<td></td>').appendTo(tr); // applies to

      var actions_col = $('<td></td>');
      actions_col.appendTo(tr);

      var actions_container = $('<span></span>', { class: 'pull-right' });
      actions_container.appendTo(actions_col)

      var uid = val.url.slice(0, val.url.length - 5);

      $('<button></button>', {"class": "btn btn-default", text: 'Edit'})
        .click(function () { editProfile(uid); })
        .appendTo(actions_container);

      $('<button></button>', {"class": "btn btn-danger", text: 'Delete'})
        .click(function () { removeProfile (uid, val.displayName); })
        .appendTo(actions_container);

      tr.appendTo('#profile-list');
    });
  });
}

function configureHypervisor() {
  $.getJSON("/hypervisor/", function(data){
    $('#host').val(data.host);
    $('#username').val(data.username);
    $('#mode option[value="' + data.mode + '"]').prop('selected', true);
    $('#adminhost').val(data.adminhost);
    $('#pubkey').html(data.pubkey);

    // Set placeholder for admin port
    var adminhost = location.hostname;
    var adminport = location.port || 80
    $('#adminhost').attr('placeholder', adminhost + ':' + adminport);

    $('#configure-hypervisor-modal').modal('show');
  });
}

function hideDomainSelection () {
  $('#favourite-apps-modal').modal('hide');
  $('#edit-profile-modal').modal('show');
}

function selectDomain() {
  $('#edit-profile-modal').modal('hide');
  $('#domain-selection-modal').modal('show');

  // Function for domain selection handling
  function domainSelected() {
    // Once selected the domain, set it's uuid in sessionStorage and redirect
    $('#domain-selection-modal').modal('hide');
    sessionStorage.setItem("fc.session.domain", $(this).attr('data-uuid'));
    sessionStorage.setItem("fc.session.profile_uid", uid);
    $('#spinner-modal').modal('show');
    setTimeout(function(){
      location.href = "/profiles/livesession";
    }, 500)
  }

  // Show loading clock
  spinner = $('#domain-selection-modal .spinner');
  list = $('#domain-selection-list');

  spinner.show();
  list.html('');

  // Generate domain list
  $.getJSON ('/hypervisor/domains/list/', function(data){
    // Hide loading clock
    $('#domain-selection-modal .spinner').hide();

    $.each(data.domains, function() {
      domain = $('<a></a>', { text: this.name, href: '#', 'data-uuid': this.uuid});
      wrapper = $('<div></div>');
      domain.appendTo(wrapper)
      wrapper.appendTo(list);
      domain.click(domainSelected);
    });

  }, function(data){
    alert(data.status)
  });
}

function saveHypervisorConfig() {
    clearModalFormErrors('configure-hypervisor-modal');

    var data = {
      host: $('#host').val(),
      username: $('#username').val(),
      mode: $('#mode').val(),
      adminhost: $('#adminhost').val(),
      domains: {}
    }

    $.ajax({
      method: 'POST',
      url: '/hypervisor/',
      data: JSON.stringify(data),
      contentType: 'application/json',
      success: function(data) {
        if (!data.errors) {
          $('#configure-hypervisor-modal').modal('hide');
        } else {
          $.each(data.errors, function( key, value ) {
            addFormError(key, value);
          });
        }
      }
    });
}

function addProfile() {
  $('#add-profile-modal').modal('show');
}

function newProfile() {
  clearModalFormErrors('add-profile-modal');

  if (!$('#profile-name').val()) {
    addFormError('profile-name', 'Profile name is required');
    return
  }

  var data = {
    'profile-name': $('#profile-name').val(),
    'profile-desc': $('#profile-desc').val(),
    'users': $('#profile-users').val(),
    'groups': $('#profile-groups').val(),
  }

  //TODO: show spinner/progress indicator
  $.ajax({
    method: 'POST',
    url: '/profiles/new',
    data: JSON.stringify(data),
    contentType: 'application/json',
  }).success (function (data) {
    $('#add-profile-modal').modal('hide');
    // Refresh profiles
    populateProfileList();
  }).fail(function() {
    showMessageDialog('Error creating profile', 'Error');
  });
}

function editProfile(profileId) {
  // Get profile id data
  $.getJSON('/profiles/' + profileId, function(data) {
    // Load data in required fields
    $('#edit-profile-name').val(data.name);
    $('#edit-profile-desc').val(data.description || '');

    // Get users and groups
    $.getJSON('/profiles/applies/' + profileId, function(data) {
      $('#edit-profile-users').val(data.users || '');
      $('#edit-profile-groups').val(data.groups || '');

      // Set global uid
      uid = profileId;
      // Show dialog
      $('#edit-profile-modal').modal('show');
    });

  });
}

// TODO: Functionality to be reviewed
function saveProfile() {
  clearModalFormErrors('edit-profile-modal');

  if (!$('#edit-profile-name').val()) {
    addFormError('edit-profile-name', 'Profile name is required');
    return
  }

  var data = {
    'profile-name': $('#edit-profile-name').val(),
    'profile-desc': $('#edit-profile-desc').val(),
    'users': $('#edit-profile-users').val(),
    'groups': $('#edit-profile-groups').val(),
  }

  //TODO: show spinner/progress indicator
  $.ajax({
    method: 'POST',
    url: '/profiles/props/' + uid,
    data: JSON.stringify(data),
    contentType: 'application/json',
  }).success (function (data) {
    $('#edit-profile-modal').modal('hide');
    // Refresh profiles
    populateProfileList();
  }).fail(function() {
    showMessageDialog('Error creating profile', 'Error');
  });
}

function removeProfile(uid, displayName) {
  $('#del-profile-name').text(displayName);
  $('#del-profile-modal').modal('show');
  $('#del-profile-confirm').click(function () {
    $.getJSON ('/profiles/delete/' + uid)
      .always(function () {
        populateProfileList();
        $('#del-profile-modal').modal('hide');
      });
  });
}

$(document).ready (function () {

  $('#add-profile').click (addProfile);
  $('#show-hypervisor-config').click(configureHypervisor);

  populateProfileList();

  // Show hypervisor dialog if not configured
  $.getJSON ('/init/', function(data){
    if (data.needcfg) {
      configure_hypervisor();
    }
  });

  var editing = sessionStorage.getItem("fc.session.profile_uid");
  if (editing) {
    sessionStorage.removeItem("fc.session.profile_uid");
    editProfile(editing);
  }

});
