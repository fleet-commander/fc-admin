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

function updateEventList () {
  $.getJSON ("/session_changes", function (data) {
    $("#event-list").html("");
    changes = data;
    $.each (data, function (i, item) {
      var row = item.join (" ");
      var id = data.length - 1 - i;
      var input = '<input type="checkbox" class="change-checkbox" data-id="' + id + '"/>';
      $("#event-list").html($("#event-list").html() + "<li>" + input + row + "</li>");
    });
    if (submit) {
      $(".change-checkbox").show();
    }
  });
}

function startVNC () {
  updater = window.setInterval (updateEventList, 1000);
}

function closeSession () {
  window.clearInterval(updater);


  $.getJSON("/session/stop", function (data) {return;});
}

function restartSession() {
  submit = false;
  closeSession();
  showSession();
  $('input[type="button"]').show();
  $(".hidden").hide();
  $('.change-checkbox').hide();

  $.getJSON("/session/start", function (data) {
    window.setTimeout(startSpice, 1000);
  });
}

function reviewChanges() {
  $("#spice-area").hide(200);
  $("#event-logs").show(200);
}

function showSession() {
  $("#spice-area").show(200);
  $("#event-logs").hide(200);
}

function createProfile() {
  submit = true;
  $('input[type="button"]').hide();
  $("#restart-profile, #submit-profile").show();
  $(".change-checkbox").show();

  window.setTimeout(function () {reviewChanges();}, 1000);

  closeSession();
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
  var vbc_rfb = new RFB({'target': $D('vnc-canvas')});
  vbc_rfb.connect('localhost', '8989', '', 'websockify');

  $.getJSON("/session/start", function (data) {
    window.setTimeout(restartSession, 1000);
  });

  $("#event-logs").hide();
});
