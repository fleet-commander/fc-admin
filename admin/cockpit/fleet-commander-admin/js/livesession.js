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
var fcsc = null;
var heartbeat = null;

var collectors = {
  'org.gnome.gsettings':
    new BaseCollector('org.gnome.gsettings'),
  'org.libreoffice.registry':
    new BaseCollector('org.libreoffice.registry'),
  'org.freedesktop.NetworkManager':
    new NMCollector('org.freedesktop.NetworkManager'),
}

window.alert = function(message) {
  DEBUG > 0 && console.log('FC: Alert message:' + message);
}

function startLiveSession() {
  // Stop any previous session
  stopLiveSession(function(){
    var domain = sessionStorage.getItem("fc.session.domain")
    var admin_host = location.hostname
    fc.SessionStart(domain, admin_host,function(resp){
      if (resp.status) {
        fcsc = new FleetCommanderSpiceClient(
          admin_host, resp.port, stopLiveSession);
        startHeartBeat();
      } else {
        showMessageDialog(resp.error, _('Error'));
      }
    })
  });
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
  $('#networkmanager-event-list').html('');

  DEBUG > 0 && console.log('FC: Populating LibreOffice change list');
  populateSectionChanges('#libreoffice-event-list',
    collectors['org.libreoffice.registry'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating GSettings change list');
  populateSectionChanges('#gsettings-event-list',
    collectors['org.gnome.gsettings'].dump_changes());

  DEBUG > 0 && console.log('FC: Populating NetworkManager change list');
  populateSectionChanges('#networkmanager-event-list',
    collectors['org.freedesktop.NetworkManager'].dump_changes());
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
}

function reviewAndSubmit() {
  $('.change-checkbox').show();
  populateChanges();
  $('#event-logs').modal('show');
}

function deployProfile() {
  var gsettings = [];
  var libreoffice = [];
  var networkmanager = [];

  $.each($('#gsettings-event-list input[data-id]:checked'), function (i,e) {
    gsettings.push($(this).attr('data-id'));
  });

  $.each($('#libreoffice-event-list input[data-id]:checked'), function (i,e) {
    libreoffice.push($(this).attr('data-id'));
  });

  $.each($('#networkmanager-event-list input[data-id]:checked'), function (i,e) {
    networkmanager.push($(this).attr('data-id'));
  });

  var changesets = {
    'org.gnome.gsettings':
      collectors['org.gnome.gsettings'].get_changeset(gsettings),
    'org.libreoffice.registry':
      collectors['org.libreoffice.registry'].get_changeset(libreoffice),
    'org.freedesktop.NetworkManager':
      collectors['org.freedesktop.NetworkManager'].get_changeset(networkmanager)
  };

  showSpinnerDialog(
    _('Saving settings to profile. Please wait...'),
    _('Saving settings'))

  stopLiveSession(function () {
    var uid = sessionStorage.getItem("fc.session.profile_uid");
    DEBUG > 0 && console.log('FC: Saving live session settings')
    fc.SessionSave(uid, changesets, function(resp){
        if (resp.status) {
          DEBUG > 0 && console.log('FC: Saved live session settings')
          location.href='index.html'
        } else {
          showMessageDialog(_('Error saving session'), _('Error'));
        }
    }, function(){
      console.log('FC: Error saving live session settings')
    });
  });
}

$(document).ready (function () {
  $('#close-live-session').click(stopLiveSession);
  $('#review-changes').click(reviewAndSubmit);
  $('#deploy-profile').click(deployProfile);

  // SPICE port changes listeners
  window.addEventListener('spice-port-data', function(event) {
    if (event.detail.channel.portName == 'org.freedesktop.FleetCommander.0') {
      var msg_text = arraybuffer_to_str(new Uint8Array(event.detail.data));
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

    fc.GetDebugLevel(function(resp) {
      setDebugLevel(resp);
    });

    $('#main-container').show();
    startLiveSession();
    // Error catchall to workarount "oops" message in cockpit
    window.onerror = function(message, url, lineNumber) {
      DEBUG > 0 && console.error('Live session error: (', lineNumber, ' ', url, ') ', message);
      return true;
    };
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
