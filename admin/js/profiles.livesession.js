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
var sc;

window.alert = function(message) {
  console.log('FC: Alert message:' + message);
}

/* SPICE HTML5 */
function spiceClientConnection(host, port) {

  var connecting = null;
  var conn_timeout = 15000; //ms
  var noretry = false;

  function set_connection_timeout() {
    console.log('trying to set timeout')
    if (!connecting) {
      console.log('setting timeout')
      connecting = setTimeout(function() {
        console.log('timeout reached')
        if (sc) sc.stop()
        $('#spice-screen').html('');
        connecting = null;
        noretry = true;
        console.log('FC: Connection tries timed out');
        $('#spinner-modal').modal('hide');
        showMessageDialog('Connection error to virtual machine.', 'Connection error');
      }, conn_timeout);
    }
  }

  function spice_connected() {
    console.log('FC: Connected to virtual machine using SPICE');
    $('#spinner-modal').modal('hide');
    if (connecting) {
      clearTimeout(connecting);
      connecting = null;
    }
  }

  function spice_error(err) {
    console.log("FC: SPICE connection error:", err.message);

    set_connection_timeout()

    if (err.message == 'Unexpected close while ready' || err.message == 'Connection timed out.' || sc.state != 'ready')  {
      if (!noretry) {
        $('#spinner-modal h4').text('Connecting to virtual machine. Please wait...');
        $('#spinner-modal').modal('show');
        do_connection();
      }
    } else {
      $('#spinner-modal').modal('hide');
      if (connecting) {
        clearTimeout(connecting);
        connecting = null;
      }
      showMessageDialog('Connection error to virtual machine.', 'Connection error');
    }

  }

  function do_connection() {
    console.log('FC: Connecting to spice session')
    if (sc) sc.stop()
    $('#spice-screen').html('');
    sc = new SpiceMainConn({
      uri: 'ws://' + location.hostname + ':' + port,
      screen_id: 'spice-screen',
      onsuccess: spice_connected,
      onerror: spice_error
      // dump_id: "debug-div",
      // message_id: "message-div",
      // password: password,
      // onagent: agent_connected,
    });
  }

  try {
    do_connection();
  } catch (e) {
    console.error('FC: Fatal error:' + e.toString());
    sessionStop();
  }

  function agent_connected(sc) {
    window.addEventListener('resize', handle_resize);
    window.spice_connection = sc;
    resize_helper(sc);
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

}

function sessionStart() {
  // Stop any previous session
  sessionStop(function(){
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
    }).done(function(data){
        spiceClientConnection(location.hostname, data.port);
        listenChanges();
    }).fail(function(jqXHR, textStatus, errorThrown){
        showMessageDialog(jqXHR.responseJSON.status, 'Error');
    });
  });
}

function sessionStop (cb) {
  if (sc) sc.stop();
  $.get("/session/stop").always(function() {
    if (!cb) {
      location.href = '/';
    } else {
      cb()
    }
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

  $('#spinner-modal h4').text('Saving settings');
  $('#spinner-modal').modal('show');

  $.ajax({method: 'POST',
          url:    '/changes/select',
          data:   JSON.stringify(changeset),
          dataType: 'json',
          contentType: 'application/json'
  }).done(function (data) {
    sessionStop(function () {
      $.ajax({
        method: 'POST',
        url:    '/session/save',
        data:   JSON.stringify({ uid: sessionStorage.getItem("fc.session.profile_uid")}),
        dataType: 'json',
        contentType: 'application/json'
      }).done(function(){
          location.href='/'
      }).fail(function(jqXHR, textStatus, errorThrown){
        showMessageDialog(jqXHR.responseJSON.status, 'Error');
      });
    });
  });
}

$(document).ready (function () {
  sessionStart();
});
