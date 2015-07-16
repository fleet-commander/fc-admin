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

var uid = "";

function populateUsersGroups(users, groups) {
  $.each(users, function (i,e) {
    console.log("bar");
    $("#profile-users").html($("#profile-users").html() + '<input type="checkbox" name="user-' + e + '">' + e + '</input>');
  });
  $.each(groups, function(i,e) {
    console.log("foo");
    $("#profile-groups").html($("#profile-groups").html() + '<input type="checkbox" name="group-' + e + '">' + e + '</input>');
  });
}

function profileSave() {
  var payload = {}
  $.each($('form').serializeArray(), function (array, input) {
    payload[input.name] = input.value;
  });

  //TODO: show spinner/progress indicator
  $.ajax({
    method: 'POST',
    url: '/profiles/save/' + uid,
    data: JSON.stringify(payload),
    contentType: 'application/json',
  }).always (function (data) {
    location.pathname = '/';
  });
}

function profileDiscard() {
  $.get("/profiles/discard/"+uid)
    .always(function () { location.pathname = "/"; });
}

$(document).ready (function () {
  var path = location.pathname.split("/");
  uid = path[path.length - 1];
});
