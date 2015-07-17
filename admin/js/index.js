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

function populate_profile_list() {
  $.ajaxSetup({cache: false});
  $.getJSON ("/profiles/", function (data) {
    $("#profile-list").html ("");
    $.each (data, function (i, val) {
      var tr = $('<tr ></tr>');
      $('<td></td>', { text: val.displayName }).appendTo(tr);
      $('<td></td>').appendTo(tr); // description
      $('<td></td>').appendTo(tr); // os
      $('<td></td>').appendTo(tr); // applies to

      var delete_col = $('<td></td>');
      delete_col.appendTo(tr);

      $('<a></a>')
        .attr('href', '#')
        .click(function () { remove_profile (val); })
        .text('X') //TODO: Use an icon
        .appendTo(delete_col);

      tr.appendTo('#profile-list');
    });
  });
}

function remove_profile(profile) {
  $('#del-profile-name').text(profile.displayName);
  $('#del-profile-modal').modal('show');
  $('#del-profile-confirm').click(function () {
    $.getJSON ('/profiles/delete/' + profile.url)
      .always(function () {
        populate_profile_list();
        $('#del-profile-modal').modal('hide');
      });
  });
}

function profile_confirmation () {
  $('#add-profile-modal').modal('show');
  $('#add-profile-confirm').click(function () {
    if ($('#host').val() == '') {
      //TODO: Check if http://hostname:8182 works
      //TODO: Check if http://hostname:VNC35 works
      $('#host-group').addClass('has-error');
      return;
    }

    $('#host-group').removeClass('has-error');
    $('#add-profile-modal').modal('hide');
    sessionStorage.setItem("fc.session.host", $('#host').val());
    location.href = "/profiles/add"
  });
}

$(document).ready (function () {
  $('#add-profile').click (profile_confirmation)
  populate_profile_list();
});
