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

function configure_hypervisor() {
  $.getJSON("/hypervisor/", function(data){
    $('#host').val(data.host);
    $('#username').val(data.username);
    $('#mode option[value="' + data.mode + '"]').prop('selected', true);
    $('#pubkey').html(data.pubkey);
    $('#configure-hypervisor-modal').modal('show');
  });
}

function select_domain() {
  $('#domain-selection-modal').modal('show');

  // Function for domain selection handling
  function domain_selected() {
    // Once selected the domain, set it's uuid in sessionStorage and redirect
    $('#domain-selection-modal').modal('hide');
    sessionStorage.setItem("fc.session.domain", $(this).attr('data-uuid'));
    location.href = "/profiles/add";
  }

  // Show loading clock
  spinner = $('#domain-selection-modal .spinner');
  list = $('#domain-selection-list');

  spinner.show();
  list.html('');

  // Generate domain list
  $.getJSON ('/hypervisor/domains/list/', function(data){
    // Hide loading clock
    if (data.status) {
      $.each(data.domains, function() {
        domain = $('<a></a>', { text: this.name, href: '#', 'data-uuid': this.uuid});
        wrapper = $('<div></div>');
        domain.appendTo(wrapper)
        wrapper.appendTo(list);
        domain.click(domain_selected);
      });
    } else {
      alert(data.error);
    }
    $('#domain-selection-modal .spinner').hide();
  });
}

function save_hypervisor_configuration() {
    if ($('#host').val() == '') {
      $('#host-group').addClass('has-error');
      return;
    }
    if ($('#username').val() == '') {
      $('#username-group').addClass('has-error');
      return;
    }
    $('#host-group').removeClass('has-error');
    $('#username-group').removeClass('has-error');
    $('#configure-hypervisor-modal').modal('hide');

    var data = {
      host: $('#host').val(),
      username: $('#username').val(),
      mode: $('#mode').val(),
      domains: {}
    }

    $.ajax({
      method: 'POST',
      url: '/hypervisor/',
      data: JSON.stringify(data),
      contentType: 'application/json',
      success: function(data) {
        $('#configure-hypervisor-modal').modal('hide');
      }
    });
}

function initialization() {
  $.getJSON ('/init/', function(data){
    if (data.needcfg) {
      configure_hypervisor();
    }
  });
}

$(document).ready (function () {

  $('#add-profile').click (select_domain);
  $('#show-hypervisor-config').click(configure_hypervisor);
  $('#configure-hypervisor-confirm').click(save_hypervisor_configuration);

  initialization();
  populate_profile_list();
});
