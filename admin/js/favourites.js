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

var uid = null;
var overrides;

function hasSuffix (haystack, needle) {
  return (haystack.length - needle.length) == haystack.lastIndexOf(needle);
}

function populateOverrides () {
  $('#overrides-list').html('');
  $.each (overrides, function (i, app) {
    addOverride (app);
  });
}

function addOverrideFromEntry () {
  var app = $('#app-name').val ();

  if (hasSuffix (app, ".desktop") == false) {
    return;
  }

  if (app.indexOf('"') != -1 || app.indexOf("'") != -1) {
    return;
  }

  if (overrides == null)
    overrdes = [];

  overrides.push (app);

  addOverride (app);
}

function insertOverride (app) {
  for (i in overrides) {
    if (overrides[i] == app)
      return;
  }

  overrides.push(app);
  populateOverrides ();
}

function addOverride (app) {
  var duplicate = false;
  if (typeof (app) != "string")
    return;
  if (hasSuffix (app, ".desktop") == false)
    return;

  var li = $('<li></li>', {'class': 'list-group-item', 'data-id': app, 'text': app });
  var del = $('<input></input>', {
    value: 'Delete',
    'class': 'pull-right btn btn-danger',
    type: 'button',
    onclick: 'deleteOverride("'+app+'")'});
  del.appendTo (li);

  li.appendTo($('#overrides-list'));
}

function deleteOverride (app) {
  if (overrides == null)
    return;

  $.each (overrides, function (i, e) {
    if (e != app)
      return;

    overrides.splice (i, 1);

    $('li[data-id="'+app+'"]').remove();
  });
}

function readFavourites () {
  $.ajax ({
    method: 'GET',
    url: '/clientdata/' + uid + ".json",
    contentType: 'application/json',
  }).done (function (data) {
    try {
      var changes = data["settings"]["org.gnome.gsettings"];
      $.each (changes, function (i,e) {
        for (key in e) {
          if (e[key] == "/org/gnome/software/popular-overrides") {
            try {
              overrides = JSON.parse(e["value"]);

              if (Array.isArray (overrides) == false) {
                overrides = null;
                return;
              }

              populateOverrides ();
              return;
            } catch (e) {
            }

            return;
          }
        }
      })
    } catch (e) {
      //TODO: Do we need to handle this situation?
    }
  }).fail (function (data) {
    //TODO: Do we need to handle this situation?
  });
}

function saveOverrides () {
  $.ajax({
    method: 'POST',
    url: location.pathname,
    data: JSON.stringify(overrides),
    contentType: 'application/json'
  })
    .done (function (data) {
      location.href = "/";
    })
    .fail (function (data) {
        //FIXME: Error dialog/feedback?
    });
  return;
}

function discard () {
  location.href = "/";
}

$(document).ready (function () {
  var path = location.pathname.split("/");
  uid =  path[path.length - 1];
  overrides = null;

  readFavourites ();
});
