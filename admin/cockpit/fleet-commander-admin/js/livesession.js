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
var updater = null;

window.alert = function(message) {
  console.log('FC: Alert message:' + message);
}

function startLiveSession() {
  // Stop any previous session
  stopLiveSession(function(){
    var domain = sessionStorage.getItem("fc.session.domain")
    var admin_host = location.hostname
    fc.SessionStart(domain, admin_host,function(resp){
      if (resp.status) {
        fcsc = new FleetCommanderSpiceClient(admin_host, resp.port, stopLiveSession);
        listenForChanges();
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

function listenForChanges() {
  updater = window.setInterval (readChanges, 1000);
}

function readChanges() {
  fc.GetChanges(function(resp){
    console.log('READ CHANGES:',resp)
    $('#gsettings-event-list').html('');
    $('#libreoffice-event-list').html('');

    if ('org.libreoffice.registry' in resp)
      populateChanges('#libreoffice-event-list', resp['org.libreoffice.registry']);
    if ('org.gnome.gsettings' in resp)
      populateChanges('#gsettings-event-list', resp['org.gnome.gsettings']);
  });
}

function populateChanges(section, data) {
  $.each (data, function (i, item) {
    var row = item.join (" ");
    var li = $('<li></li>');
    var p  = $('<div></div>', {text: row}).appendTo(li);
    li.appendTo($(section));
    $('<input/>', {type:  'checkbox', class: 'change-checkbox', 'data-id': item[0]})
      .click (function (e) {
        e.stopImmediatePropagation();
      })
      .prependTo(li);
  });
}

function reviewAndSubmit() {
  clearInterval(updater);
  $('.change-checkbox').show();
  $('#event-logs').modal('show');
}

function deployProfile() {
  var gsettings = [];
  var libreoffice = [];

  $.each($('#gsettings-event-list input[data-id]:checked'), function (i,e) {
    gsettings.push($(this).attr('data-id'));
  });

  $.each($('#libreoffice-event-list input[data-id]:checked'), function (i,e) {
    libreoffice.push($(this).attr('data-id'));
  });

  var changeset = {"org.libreoffice.registry": libreoffice,
                   "org.gnome.gsettings":      gsettings};

  $('#spinner-modal h4').text(_('Saving settings'));
  $('#spinner-modal').modal('show');

  fc.SelectChanges(changeset, function(resp){
    if (resp.status) {
      stopLiveSession(function () {
        var uid = sessionStorage.getItem("fc.session.profile_uid");
        fc.SessionSave(uid, function(){
            if (resp.status) {
              location.href='index.html'
            } else {
              showMessageDialog(_('Error saving session'), _('Error'));
            }
        });
      });
    } else {
      showMessageDialog(_('Error saving settings'), _('Error'));
    }
  });
}

$(document).ready (function () {
  $('#close-live-session').click(stopLiveSession);
  $('#review-changes').click(reviewAndSubmit);
  $('#deploy-profile').click(deployProfile);
  $('#close-review, #back_review').click(listenForChanges);

  fc = new FleetCommanderDbusClient();
  startLiveSession();
});
