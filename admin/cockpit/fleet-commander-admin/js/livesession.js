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

var DEBUG = 0;
var _ = cockpit.gettext
var fc = null;
var fcsc = null;
var heartbeat = null;

var collectors = {
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
    new NMCollector('org.freedesktop.NetworkManager'),
}

window.alert = function(message) {
  DEBUG > 0 && console.log('FC: Alert message:' + message);
}

function startLiveSession() {
  spinnerDialog.show(
    _('Connecting to virtual machine')
  );
  // Stop any previous session
  stopLiveSession(function(){
    var domain = sessionStorage.getItem("fc.session.domain")
    fc.SessionStart(domain, function(resp){
      if (resp.status) {
        fcsc = new FleetCommanderSpiceClient(
          location.hostname, resp.port, function () {
            stopLiveSession()
          });
        startHeartBeat();
      } else {
        messageDialog.show(resp.error, _('Error'));
        spinnerDialog.close();
      }
    })
  });
}

function reconnectToVM() {
  if (fcsc) fcsc.reconnect();
}

function stopLiveSession(cb) {
  if (fcsc) fcsc.stop();
  fc.SessionStop(function(resp){
    if (typeof(cb) === 'function') {
      cb()
    } else {
      location.href = 'index.html';
    }
  });
}

function startHeartBeat() {
  heartbeat = window.setInterval (function(){
    fc.HeartBeat(function(resp){
      DEBUG > 0 && console.log('FC: Heartbeat:', resp)
    });
  }, 1000);
}

function populateChanges() {
  $('#gsettings-event-list').html('');
  $('#libreoffice-event-list').html('');
  $('#chromium-event-list').html('');
  $('#chrome-event-list').html('');
  $('#firefox-event-list').html('');
  $('#firefoxbookmarks-event-list').html('');
  $('#networkmanager-event-list').html('');

  DEBUG > 0 && console.log('FC: Populating LibreOffice change list');
  populateSectionChanges('#libreoffice-event-list',
    collectors['org.libreoffice.registry'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating GSettings change list');
  populateSectionChanges('#gsettings-event-list',
    collectors['org.gnome.gsettings'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating Chromium change list');
  populateSectionChanges('#chromium-event-list',
    collectors['org.chromium.Policies'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating Chrome change list');
  populateSectionChanges('#chrome-event-list',
    collectors['com.google.chrome.Policies'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating Firefox change list');
  populateSectionChanges('#firefox-event-list',
   collectors['org.mozilla.firefox'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating Firefox bookmarks change list');
  populateSectionChanges('#firefoxbookmarks-event-list',
  collectors['org.mozilla.firefox.Bookmarks'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating NetworkManager change list');
  populateSectionChanges('#networkmanager-event-list',
    collectors['org.freedesktop.NetworkManager'].dump_changes());
}

function addSectionCheckbox(section) {
  var section_header = $(section).prev("h4");
  var chkbox_container = $(
    '<div/>',
    {
      class: 'list-view-pf-checkbox',
      id: section.replace("#", "") + '-chkbox-container'
    }
  );
  var checkbox = $('<input/>', {type: 'checkbox'});
  checkbox.click(function() {
    var sectionChecked = this.checked;
    $(section).find('input[type=checkbox]').each(function() {
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
  $.each (data, function (i, item) {
    if (only_value) {
      var row = item[1];
    } else {
      var row = item.join (" ");
    }
    var citem = $($('#change-item-template').html());
    citem.appendTo($(section));
    checkbox = citem.find('input[type=checkbox]');
    checkbox.attr('data-id', item[0]);
    citem.find('.changekey').html(row);
  });

  removeSectionCheckbox(section);
  if (data.length) {
    addSectionCheckbox(section);
  }
}

function reviewAndSubmit() {
  $('.change-checkbox').show();
  populateChanges();
  $('#event-logs').modal('show');
}

function deployProfile() {
  var gsettings = [];
  var libreoffice = [];
  var chromium = [];
  var chrome = [];
  var firefox = [];
  var firefoxbookmarks = [];
  var networkmanager = [];

  $.each($('#gsettings-event-list input[data-id]:checked'), function (i,e) {
    gsettings.push($(this).attr('data-id'));
  });

  $.each($('#libreoffice-event-list input[data-id]:checked'), function (i,e) {
    libreoffice.push($(this).attr('data-id'));
  });

  $.each($('#chromium-event-list input[data-id]:checked'), function (i,e) {
    chromium.push($(this).attr('data-id'));
  })

  $.each($('#chrome-event-list input[data-id]:checked'), function (i,e) {
    chrome.push($(this).attr('data-id'));
  })

  $.each($('#firefox-event-list input[data-id]:checked'), function (i,e) {
    firefox.push($(this).attr('data-id'));
  })

  $.each($('#firefoxbookmarks-event-list input[data-id]:checked'), function (i,e) {
    firefoxbookmarks.push($(this).attr('data-id'));
  })

  $.each($('#networkmanager-event-list input[data-id]:checked'), function (i,e) {
    networkmanager.push($(this).attr('data-id'));
  });

  var changesets = {
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
    DEBUG > 0 && console.log('FC: Saving live session settings')
    fc.SessionSave(uid, changesets, function(resp){
        if (resp.status) {
          DEBUG > 0 && console.log('FC: Saved live session settings')
          location.href='index.html'
        } else {
          messageDialog.show(
            _('Error saving session'),
            _('Error')
          );
          spinnerDialog.close();
        }
    }, function(){
      console.log('FC: Error saving live session settings')
    });
  });
}

$(document).ready (function () {
  $('#reconnect-to-vm').click(reconnectToVM);
  $('#close-live-session').click(stopLiveSession);
  $('#review-changes').click(reviewAndSubmit);
  $('#deploy-profile').click(deployProfile);

  spinnerDialog = new SpinnerDialog();
  messageDialog = new MessageDialog();

  // SPICE port changes listeners
  window.addEventListener('spice-port-data', function(event) {
    if (event.detail.channel.portName == 'org.freedesktop.FleetCommander.0') {
      var msg_text = arraybuffer_to_str_func(new Uint8Array(event.detail.data));
      DEBUG > 0 && console.log(
        'FC: Logger data received in spice port',
        event.detail.channel.portName,
        msg_text);
      try {
        var change = JSON.parse(msg_text);
        DEBUG > 0 && console.log(
          'FC: Change parsed', change);
        if (change.ns in collectors) {
          collectors[change.ns].handle_change(JSON.parse(change.data));
        } else {
          DEBUG > 0 && console.log(
            'FC: Unknown change namespace', change.ns);
        }
      } catch (e) {
        DEBUG > 0 && console.log(
          'FC: Error while parsing change', msg_text);
      }
    }
  });

  window.addEventListener('spice-port-event', function(event) {
    if (event.detail.channel.portName == 'org.freedesktop.FleetCommander.0') {
      if (event.detail.spiceEvent[0] == 0) {
        DEBUG > 0 && console.log(
          'FC: Logger connected to SPICE channel');
      } else if (event.detail.spiceEvent[0] == 1) {
        DEBUG > 0 && console.log(
          'FC: Logger disconnected to SPICE channel');
      } else {
        DEBUG > 0 && console.log(
          'FC: Unknown event received in SPICE channel',
          event.detail.spiceEvent);
      }

    }
  });

  // Create a Fleet Commander dbus client instance
  fc = new FleetCommanderDbusClient(function(){

    fc.GetInitialValues(function(resp) {
      setDebugLevel(resp.debuglevel);

      // Try domain connection
      fc.DoDomainConnection(function(resp) {
          if (resp.status) {
            $('#main-container').show();
            startLiveSession();
            // Error catchall to workarount "oops" message in cockpit
            window.onerror = function(message, url, lineNumber) {
              DEBUG > 0 && console.error('Live session error: (', lineNumber, ' ', url, ') ', message);
              return true;
            };
          } else {
            fc.Quit();
            $('#main-container').hide()
            console.log(resp.error);
            showCurtain(
              _('Error connecting to FC service. Check system logs for details'),
              _('Error connecting to FC service'),
              null,
              {
                'dbus-retry': {
                  text: 'Retry connection',
                  class: 'btn-primary',
                  callback: function(){ location.reload() }},
              });
          }
      })

    });
  }, function(){
    $('#main-container').hide()
    showCurtain(
      _('Can not connect with Fleet Commander dbus service'),
      _('Can\'t connect to Fleet Commander'),
      null,
      {
        'dbus-retry': {
          text: 'Retry connection',
          class: 'btn-primary',
          callback: function(){ location.reload() }},
      });
  });

});
