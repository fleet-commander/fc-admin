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

/*******************************************************************************
 * Utility functions
 ******************************************************************************/

function showMessageDialog(message, title, closecb) {
  title = title || 'Info';
  var dialog = $('#message-dialog-modal');
  closecb = closecb || function() { dialog.modal('hide') }
  $('#message-dialog-modal h4').html(title);
  $('#message-dialog-modal .modal-body').html(message);
  var modal_footer = $('#message-dialog-modal .modal-footer');
  modal_footer.html('');
  var closebutton =  $('<button></button>', {"class": "btn btn-primary", text: _('Close')})
    .click(closecb)
    .appendTo(modal_footer);
  dialog.modal('show');
}

function showQuestionDialog(message, title, acceptcb, cancelcb) {
  title = title || 'Question';
  var dialog = $('#message-dialog-modal');
  cancelcb = cancelcb || function() { dialog.modal('hide') }
  $('#message-dialog-modal h4').html(title);
  $('#message-dialog-modal .modal-body').html(message);
  var modal_footer = $('#message-dialog-modal .modal-footer');
  modal_footer.html('');
  var acceptbutton =  $('<button></button>', {"class": "btn btn-primary", text: _('Ok')})
    .click(acceptcb)
    .appendTo(modal_footer);
  var cancelbutton =  $('<button></button>', {"class": "btn btn-default", text: _('Cancel')})
    .click(cancelcb)
    .appendTo(modal_footer);
  dialog.modal('show');
}


function clearModalFormErrors(modalId) {
  $('#' + modalId + ' div.form-group').removeClass('has-error');
  $('#' + modalId + ' div.form-group > .error-message').remove();
}

function addFormError(fieldId, errorMessage) {
  $('#' + fieldId + '-group').append('<div class="help-block error-message">' + errorMessage + '</div>')
  $('#' + fieldId + '-group').addClass('has-error');
}

function hasSuffix (haystack, needle) {
  return (haystack.length - needle.length) == haystack.lastIndexOf(needle);
}
