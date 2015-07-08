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
 * Author: Alberto Ruiz <aruiz@redhat.com>
 */

var updater;
var changes;
var submit=false;
var tries=0;
var MAXTRIES=5;

function updateEventList () {
  $.getJSON ("/session/changes", function (data) {
    $("#event-list").html("");
    changes = data;
    $.each (data, function (i, item) {
      var row = item.join (" ");
      var id = data.length - 1 - i;
      var li = $('<li></li>');
      var p  = $('<div></div>', {text: row}).appendTo(li);
      li.appendTo($('#event-list'));
      $('<input/>', {type:  'checkbox', class: 'change-checkbox', 'data-id': id})
        .click (function (e) {
          e.stopImmediatePropagation();
        })
        .prependTo(li);
    });
    if (submit) {
      $(".change-checkbox").show();
    }
  });
}

function closeSession () {
  window.clearInterval(updater);

  $.post("/session/stop", { host: sessionStorage.getItem("fc.session.host") });
}

function vnc_update_state (rfb, state, oldstate, statusMsg) {
  if (state != 'disconnected')
    return;

  if (tries >= MAXTRIES) {
    //TODO: Show an error dialog
    closeSession();

    tries = 0;
    return;
  }

  tries++;
  rfb.connect(location.hostname, '8989', '', '');
}

function vncConnect() {
  var vbc_rfb = new RFB({'target': $D('vnc-canvas')});
  vbc_rfb.set_onUpdateState(vnc_update_state);
  vbc_rfb.connect(location.hostname, '8989', '', '');
}

function restartSession() {
  submit = false;
  closeSession();

  $("#top-button-box").show();
  $('.change-checkbox').hide();

  $.ajax({
    method: 'POST',
    url:    '/session/start',
    data:   { host: sessionStorage.getItem("fc.session.host")},
    complete: function (xhr, statusText) {
      if (xhr.status == 200) {
        listenChanges();
        vncConnect();
      }

      //TODO: Inform about other errors to user
      if (xhr.status == 403) {
        console.log(xhr.responseJSON.status);
      }

      //Unknown error
    },
    dataType: "json"
  });
}

function reviewAndSubmit() {
  window.clearInterval(updater);
  $('.change-checkbox').show();
  $('#event-logs').modal('show');
}

function listenChanges() {
  updater = window.setInterval (updateEventList, 1000);
}

function deployProfile() {
  var sel = [];

  $.each($('input[data-id]:checked'), function (i,e) {
    sel.push(changes.length - 1 - $(this).attr('data-id'));
  });

  //FIXME: Close session
  $.ajax({method: 'POST',
          url:    '/session/select',
          data:   JSON.stringify({'sel': sel}),
          dataType: 'json',
          contentType: 'application/json'
  }).done(function (data) {
    if (data.status == 'ok')
      location.pathname = '/deploy/' + data.uuid;
  });
}

$(document).ready (function () {
  restartSession();
});
