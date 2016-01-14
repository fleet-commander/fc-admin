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
var overrides = null;

function hasSuffix (haystack, needle) {
  return (haystack.length - needle.length) == haystack.lastIndexOf(needle);
}

function populateOverrides () {
  $.each (overrides, function (i, app) {
    addOverride (app);
  });
}

function addOverrideFromEntry () {
  clearModalFormErrors('favourite-apps-modal');

  var app = $('#app-name').val ();

  if (hasSuffix (app, ".desktop") == false) {
    showMessageDialog('Application identifier must have .desktop extension', 'Invalid entry');
  }

  if (app.indexOf('"') != -1 || app.indexOf("'") != -1) {
    showMessageDialog('Application identifier must not contain quotes', 'Invalid entry');
  }

  if (overrides == null) {
    overrides = [];
  }

  for (i in overrides) {
    if (overrides[i] == app) {
      showMessageDialog('Application identifier is already in favourites', 'Invalid entry');
      return
    }
  }

  overrides.push (app);

  addOverride (app);

  $('#app-name').val ('');
}

function addOverride (app) {

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
  }).success (function (data) {
    try {
      var changes = data["settings"]["org.gnome.gsettings"];
      $.each (changes, function (i,e) {
        for (key in e) {
          if (e[key] == "/org/gnome/software/popular-overrides") {
            try {
              overrides = e["value"];

              if (Array.isArray (overrides) == false) {
                overrides = null;
              }

              populateOverrides ();
              return;

            } catch (e) {
            }
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
    url: '/profiles/apps/' + uid,
    data: JSON.stringify(overrides),
    contentType: 'application/json'
  }).success (function (data) {
    hideFavouritesDialog();
  }).fail (function (data) {
    showMessageDialog('Error saving preferred apps', 'Error');
  });
}

function hideFavouritesDialog () {
  $('#favourite-apps-modal').modal('hide');
  $('#edit-profile-modal').modal('show');
}

function showFavouritesDialog () {
  overrides = null;
  $('#overrides-list').html('');
  $('#edit-profile-modal').modal('hide');
  $('#favourite-apps-modal').modal('show');
  readFavourites ();
}

