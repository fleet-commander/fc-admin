//
// Copyright (C) 2019  FleetCommander Contributors see COPYING for license
//

/*******************************************************************************
 * Dialogs
 ******************************************************************************/

/*jslint nomen:true */
/*global $ */
/*global _ */

const _ = cockpit.gettext;

function BaseDialog(id) {
    var self = this,
        hidn_ev = 'hidden.bs.modal',
        shn_ev = 'shown.bs.modal';
    this.id = id;

    /* state can be 'hide', 'show' or 'notset' */
    this.state = 'hide';

    $(this.id).off(hidn_ev).on(hidn_ev, function () {
        if (self.state === 'show') {
            $(this).modal('show');
        }
        self.state = 'notset';
    });

    $(this.id).off(shn_ev).on(shn_ev, function () {
        if (self.state === 'hide') {
            $(this).modal('hide');
        }
        self.state = 'notset';
    });
}

BaseDialog.prototype = {
    show: function () {
        this.state = 'show';
        $(this.id).modal('show');
    },
    close: function () {
        this.state = 'hide';
        $(this.id).modal('hide');
    }
};

function SpinnerDialog() {
    var id = '#spinner-dialog-modal',
        default_title = _('Loading');
    BaseDialog.apply(this, [id]);

    this.show = function (message, title) {
        title = title || default_title;
        $(id + ' h4').html(title);
        $(id + ' .modal-body p').html(message);
        BaseDialog.prototype.show.apply(this);
    };
}

SpinnerDialog.prototype = Object.create(BaseDialog.prototype);
SpinnerDialog.prototype.constructor = SpinnerDialog;

function QuestionDialog() {
    var self = this,
        id = '#question-dialog-modal',
        default_title = _('Question');
    BaseDialog.apply(this, [id]);

    this.show = function (message, title, acceptcb, cancelcb) {
        title = title || default_title;
        cancelcb = cancelcb || function () { self.close(); };
        $(id + ' h4').html(title);
        $(id + ' .modal-body').html(message);
        $(id + ' .modal-footer').html('');
        $('<button/>', {
            class: 'btn btn-default',
            text: _('Cancel')
        }).click(cancelcb).appendTo(id + ' .modal-footer');
        $('<button/>', {
            class: 'btn btn-primary',
            text: _('Ok')
        }).click(acceptcb).appendTo(id + ' .modal-footer');

        $(id).off('keypress').keypress(function (e) {
            var code = e.keyCode || e.which;
            if (code === 13) {
                acceptcb();
            }
        });
        BaseDialog.prototype.show.apply(this);
    };
}

QuestionDialog.prototype = Object.create(BaseDialog.prototype);
QuestionDialog.prototype.constructor = QuestionDialog;

function MessageDialog() {
    var self = this,
        id = '#message-dialog-modal',
        default_title = _('Info');
    BaseDialog.apply(this, [id]);

    this.show = function (message, title, closecb) {
        title = title || default_title;
        closecb = closecb || function () { self.close(); };
        $(id + ' h4').html(title);
        $(id + ' .modal-body').html(message);
        $(id + ' .modal-footer').html('');
        $('<button/>', {
            class: 'btn btn-primary',
            text: _('Close')
        }).click(closecb).appendTo(id + ' .modal-footer');

        $(id).off('keypress').keypress(function (e) {
            var code = (e.keyCode || e.which);
            if (code === 13) {
                closecb();
            }
        });
        BaseDialog.prototype.show.apply(this);
    };
}

MessageDialog.prototype = Object.create(BaseDialog.prototype);
MessageDialog.prototype.constructor = MessageDialog;

function showCurtain(message, title, icon, buttons) {
    var iconarea = $('#curtain .blank-slate-pf-icon'),
        buttonsarea = $('#curtain .blank-slate-pf-main-action');
    icon = icon || 'exclamation-circle';
    buttons = buttons || {};
    $('#curtain h1').html(title);
    $('#curtain p').html(message);
    if (icon !== 'spinner') {
        iconarea.html('<i class="fa fa-' + icon + '"></i>');
    } else {
        iconarea.html('<div class="spinner spinner-lg"></div>');
    }

    buttonsarea.html('');
    $.each(buttons, function (id, data) {
        var btnclass = data.class || 'btn-default',
            button = $('<button id="' + id + '" class="btn btn-lg ' + btnclass + '">' + data.text + '</button>');
        button.click(data.callback);
        buttonsarea.append(button);
        buttonsarea.append(' ');
    });
    $('#curtain').show();
}

export { MessageDialog, QuestionDialog, SpinnerDialog, showCurtain };
