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


var updater;
var submit=false;
var tries=0;
var MAXTRIES=5;

/* SPICE HTML5 */
var sc;

function spice_client_connection(host, port) {

  function spice_error(parm1, parm2, parm3, parm4) {
    console.log('ERROR ON THE ROCKS:', parm1, parm2, parm3, parm4);
  }

  function agent_connected(sc) {
    window.addEventListener('resize', handle_resize);
    window.spice_connection = this;
    resize_helper(this);
    if (window.File && window.FileReader && window.FileList && window.Blob) {
      var spice_xfer_area = document.createElement("div");
      spice_xfer_area.setAttribute('id', 'spice-xfer-area');
      document.getElementById('spice-area').appendChild(spice_xfer_area);
      document.getElementById('spice-area').addEventListener('dragover', handle_file_dragover, false);
      document.getElementById('spice-area').addEventListener('drop', handle_file_drop, false);
    }
    else {
      console.log("File API is not supported");
    }
  }

  try {
    setTimeout(function() {
      sc = new SpiceMainConn({
        uri: 'ws://' + location.hostname + ':' + port,
        screen_id: "spice-screen",
        // dump_id: "debug-div",
        // message_id: "message-div",
        // password: password,
        onerror: spice_error,
        // onagent: agent_connected
      });
    },2000)
  } catch (e) {
    alert(e.toString());
    session_stop();
  }
}

function session_start() {
  data = {
    domain: sessionStorage.getItem("fc.session.domain"),
    admin_host: location.hostname,
    admin_port: location.port || 80
  }
  $.ajax({
    method: 'POST',
    url: '/session/start',
    data: JSON.stringify(data),
    contentType: 'application/json',
    success: function(data) {
      spice_client_connection(location.hostname, data.port);
      listenChanges();
    }
  })
}

function session_stop () {
  sc.stop();
  $.get("/session/stop", function() {
    location.href = '/';
  });
}


function updateEventList () {
  $.getJSON ("/changes", function (data) {
    $("#gsettings-event-list").html("");
    $("#libreoffice-event-list").html("");

    if ("org.libreoffice.registry" in data)
      populateChanges("#libreoffice-event-list", data["org.libreoffice.registry"]);
    if ("org.gnome.gsettings" in data)
      populateChanges("#gsettings-event-list", data["org.gnome.gsettings"]);

    if (submit) {
      $(".change-checkbox").show();
    }
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

function closeSession () {
  window.clearInterval(updater);
  $.get("/session/stop");
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
    contentType: 'application/json',
    data:   JSON.stringify({ host: sessionStorage.getItem("fc.session.host") }),
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

  $.ajax({method: 'POST',
          url:    '/changes/select',
          data:   JSON.stringify(changeset),
          dataType: 'json',
          contentType: 'application/json'
  }).done(function (data) {
    $.get('/session/stop').always(function () {
      if (data.status == 'ok')
        location.pathname = '/deploy/' + data.uuid;
    });
  });
}

$(document).ready (function () {
  session_start();
  // restartSession();
});
