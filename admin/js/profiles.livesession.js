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

window.alert = function(message) {
  console.log('ALERT:' + message);
}

/* SPICE HTML5 */
var sc;
var connecting = null;
var tries=0;
var maxtries=5;
var noretry=false;
var retrying=null;

function spiceClientConnection(host, port) {

  function spice_error(err) {
    console.log("SPICE ERROR: ", err);

    if (!retrying && !noretry) {
      if (err == 'Error: Unexpected close while ready' || err == 'Error: Connection timed out.' || sc.state != 'ready')  {
        if (tries >= maxtries) {
          console.log('Max reconnect tries (' + maxtries + ') reached');
          showMessageDialog('Connection error to virtual machine.', 'Connection error');
          noretry = true;
        } else {
          // Try to reconnect
          retrying = setTimeout(function() {
            tries += 1
            console.log('Reconnecting (' + tries + ')');
            $('canvas').remove();
            do_connection();
          }, 1000);
        }
      }
    }

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

  function do_connection() {
    console.log('Connecting to spice session')
    $('#spinner-modal h4').text('Connection lost. Trying to reconnect');
    $('#spinner-modal').modal('show');
    sc = new SpiceMainConn({
      uri: 'ws://' + location.hostname + ':' + port,
      screen_id: "spice-screen",
      // dump_id: "debug-div",
      // message_id: "message-div",
      // password: password,
      // onagent: agent_connected
      onerror: spice_error
    });
    $('#spinner-modal').modal('hide');
    connecting = null;
  }

  try {
    do_connection();
  } catch (e) {
    console.error('Fatal error:' + e.toString());
    sessionStop();
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
