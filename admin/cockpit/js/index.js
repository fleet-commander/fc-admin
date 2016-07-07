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

var _ = cockpit.gettext
var fc = null;
var currentuid = null;

/*******************************************************************************
 * Hypervisor configuration
 ******************************************************************************/

function checkHypervisorConfig(cb) {
  // Show hypervisor dialog if not configured
  fc.GetHypervisorConfig(function(data) {
    if (data.needcfg) {
      configureHypervisor();
    } else {
      if (cb) cb()
    }
  });
}

function showHypervisorConfig() {
  fc.GetHypervisorConfig(function(resp) {
    $('#host').val(resp.host);
    $('#username').val(resp.username);
    $('#mode option[value="' + resp.mode + '"]').prop('selected', true);
    $('#adminhost').val(resp.adminhost);
    $('#pubkey').html(resp.pubkey);
    $('#hypervisor-config-modal').modal('show');
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

  fc.SetHypervisorConfig(data, function(resp) {
    if (resp.status) {
      $('#hypervisor-config-modal').modal('hide');
    } else {
      $.each(resp.errors, function( key, value ) {
        addFormError(key, value);
      });
    }
  });
}


/*******************************************************************************
 * Profiles
 ******************************************************************************/

function refreshProfileList() {
 // Populate profiles list
 fc.GetProfiles(function(resp) {
   if (resp.status) {
     var data = resp.data;
     // Clear profile list HTML
     $('#profile-list').html('');
     // Populate profile list
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

       $('<button></button>', {"class": "btn btn-default", text: _('Edit')})
         .click(function () { editProfile(uid); })
         .appendTo(actions_container);

       $('<button></button>', {"class": "btn btn-danger", text: _('Delete')})
         .click(function () { removeProfile (uid, val.displayName); })
         .appendTo(actions_container);

       tr.appendTo('#profile-list');
     });
   } else {
     showMessageDialog(resp.error, 'Error');
   }
 });
}

function showAddProfile() {
  $('#add-profile-modal').modal('show');
}

function saveNewProfile() {
  clearModalFormErrors('add-profile-modal');

  if (!$('#profile-name').val()) {
    addFormError('profile-name', _('Profile name is required'));
    return
  }

  var data = {
    'profile-name': $('#profile-name').val(),
    'profile-desc': $('#profile-desc').val(),
    'users': $('#profile-users').val(),
    'groups': $('#profile-groups').val(),
  }

  // TODO: Show spinner
  fc.NewProfile(data, function(resp) {
    if (resp.status) {
      $('#add-profile-modal').modal('hide');
      // Refresh profiles
      refreshProfileList();
    } else {
      showMessageDialog(_('Error creating profile'), _('Error'));
    }
  });
}

function editProfile(uid) {
  fc.GetProfile(uid, function(resp) {
    if (resp.status) {
      $('#edit-profile-name').val(resp.data.name);
      $('#edit-profile-desc').val(resp.data.description || '');

      // Get users and groups
      fc.GetProfileApplies(uid, function(resp) {
        if (resp.status) {
          $('#edit-profile-users').val(resp.data.users || '');
          $('#edit-profile-groups').val(resp.data.groups || '');

          currentuid = uid;
          $('#edit-profile-modal').modal('show');
        } else {
          showMessageDialog(_('Error getting profile users and groups data'), _('Error'));
        }
      });
    } else {
      showMessageDialog(_('Error getting profile data'), _('Error'));
    }
  });
}

// TODO: Functionality to be reviewed
function saveExistingProfile() {
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
  fc.ProfileProps(data, currentuid, function(resp){
    if (resp.status) {
      $('#edit-profile-modal').modal('hide');
      refreshProfileList();
    } else {
      showMessageDialog(_('Error saving profile'), ('Error'));
    }
  });
}

function removeProfile(uid, displayName) {
  $('#del-profile-name').text(displayName);
  $('#del-profile-modal').modal('show');
  $('#del-profile-confirm').click(function () {
    fc.DeleteProfile(uid, function(resp){
      refreshProfileList();
      $('#del-profile-modal').modal('hide');
    });
  });
}

/*******************************************************************************
 * Favourites
 ******************************************************************************/

function showHighlightedApps () {
  $('#highlighted-apps-list').html('');
  $('#edit-profile-modal').modal('hide');
  $('#highlighted-apps-modal').modal('show');
  refreshHighlightedAppsList();
}

function refreshHighlightedAppsList () {
  fc.GetProfile(currentuid, function(resp) {
    if (resp.status) {
      try {
        var changes = resp.data.settings["org.gnome.gsettings"];
        $.each (changes, function (i,e) {
          for (key in e) {
            if (e[key] == "/org/gnome/software/popular-overrides") {
              try {
                var overrides = e["value"];
                if (Array.isArray (overrides) == false) {
                  overrides = null;
                }
                $.each (overrides, function(i, app) {
                  addHighlightedApp(app);
                });
                return;
              } catch (e) {
              }
            }
          }
        })
      } catch (e) {
      }
    } else {
      showMessageDialog(_('Error getting highlighted apps data'), _('Error'));
    }
  });
}

function addHighlightedApp(app) {
  if (typeof (app) != "string")
    return;

  if (hasSuffix (app, ".desktop") == false)
    return;

  var li = $('<li></li>', {'class': 'list-group-item', 'data-id': app, 'text': app });
  var del = $('<button></button>', {
    'class': 'pull-right btn btn-danger',
    text: 'Delete'
  });
  del.click(app, function() { deleteHighlightedApp(app); });
  del.appendTo (li);
  li.appendTo($('#highlighted-apps-list'));
}

function addHighlightedAppFromEntry () {
  clearModalFormErrors('highlighted-apps-modal');

  var app = $('#app-name').val ();

  if (hasSuffix(app, ".desktop") == false) {
    showMessageDialog(_('Application identifier must have .desktop extension'), _('Invalid entry'));
    return
  } else if (app.indexOf('"') != -1 || app.indexOf("'") != -1) {
    showMessageDialog(_('Application identifier must not contain quotes'), _('Invalid entry'));
    return
  } else if ($('#highlighted-apps-list li[data-id="' + app + '"]').length > 0) {
    showMessageDialog(_('Application identifier is already in favourites'), _('Invalid entry'));
    return
  }
  addHighlightedApp(app);
  $('#app-name').val('');
}

function deleteHighlightedApp(app) {
  $('#highlighted-apps-list li[data-id="' + app + '"]').remove();
}

function saveHighlightedApps () {
  var overrides = []
  $('#highlighted-apps-list li').each(function() {
    overrides.push($(this).attr('data-id'));
  })
  fc.HighlightedApps(overrides, currentuid, function(resp){
    if (resp.status) {
      $('#highlighted-apps-modal').modal('hide');
      $('#edit-profile-modal').modal('show');
    } else {
      showMessageDialog(_('Error saving highlighted apps'), _('Error'));
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
  $('#spinner-modal').modal('show');
  setTimeout(function(){
    location.href = "livesession.html";
  }, 500)
}

function showDomainSelection() {

  checkHypervisorConfig(function() {
    $('#edit-profile-modal').modal('hide');
    $('#domain-selection-modal').modal('show');

    // Show loading clock
    spinner = $('#domain-selection-modal .spinner');
    list = $('#domain-selection-list');
    spinner.show();

    // Generate domain list
    list.html('');

    fc.ListDomains(function(resp) {
      if (resp.status) {
        $('#domain-selection-modal .spinner').hide();
        $.each(resp.domains, function() {
          domain = $('<a></a>', { text: this.name, href: '#', 'data-uuid': this.uuid});
          wrapper = $('<div></div>');
          domain.appendTo(wrapper)
          wrapper.appendTo(list);
          domain.click(selectDomain);
        });
      } else {
        $('#domain-selection-modal').modal('hide');
        showMessageDialog(_('Error getting domain list'), _('Error'));
      }
    });
  });
}


/*******************************************************************************
 * Initialization
 ******************************************************************************/
$(document).ready (function () {
  // Bind events
  $('#show-hypervisor-config').click(showHypervisorConfig);
  $('#save-hypervisor-config').click(saveHypervisorConfig);
  $('#show-add-profile').click(showAddProfile);
  $('#save-new-profile').click(saveNewProfile);
  $('#save-existing-profile').click(saveExistingProfile);
  $('#show-highlighted-apps').click(showHighlightedApps);
  $('#add-highlighted-app').click(addHighlightedAppFromEntry);
  $('#save-highlighted-apps').click(saveHighlightedApps);
  $('#show-domain-selection').click(showDomainSelection);

  // Set placeholder for admin port in hypervisor configuration dialog
  var adminhost = location.hostname;
  var adminport = location.port || 80
  $('#adminhost').attr('placeholder', adminhost + ':' + adminport);

  // Create a Fleet Commander dbus client instance
  fc = new FleetCommanderDbusClient();
  refreshProfileList();
  checkHypervisorConfig();

});
