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
      li.appendTo($('#event-list'));
      li.text(row);
      $('<input/>', {type: 'checkbox', class: 'change-checkbox', 'data-id': id}).prependTo(li);

      //var input = '<input type="checkbox" class="change-checkbox" data-id="' + id + '"/>';
      //$("#event-list").html($("#event-list").html() + "<li>" + input + row + "</li>");
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
  showSession();

  $("#top-button-box").show();

  $('.change-checkbox').hide();
  $("#event-logs").hide();
  $("#restart-profile, #submit-profile").hide();

  $.ajax({
    method: 'POST',
    url:    '/session/start',
    data:   { host: sessionStorage.getItem("fc.session.host")},
    complete: function (xhr, statusText) {
      if (xhr.status == 200) {
        updater = window.setInterval (updateEventList, 1000);
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

function reviewChanges() {
  $("#vnc-area").hide(200);
  $("#event-logs").show(200);
}

function showSession() {
  $("#vnc-area").show(200);
  $("#event-logs").hide(200);
}

function createProfile() {
  submit = true;
  $('#top-button-box').hide();
  reviewChanges();
  closeSession();

  $(".change-checkbox").show();
  $("#restart-profile, #submit-profile").show();
}

function deployProfile() {
  var sel = [];
  $.each($('input[data-id]:checked'), function (i,e) {
    sel.push(changes.length - 1 - $(this).attr('data-id'));
  });
  $.post("/session/select", {"sel": sel}, function (data) {
      if (data.status == "ok") {
        location.pathname = "/deploy/" + data.uuid;
      }
  }, "json");
}

$(document).ready (function () {
  restartSession();

});
