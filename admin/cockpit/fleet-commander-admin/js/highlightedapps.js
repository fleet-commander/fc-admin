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
* Author: Oliver Gutiérrez <ogutierrez@redhat.com>
*/
import { DEBUG, hasSuffix, clearModalFormErrors } from './base.js';
import { messageDialog } from './dialogs.js';

const _ = cockpit.gettext;

class HighlightedApp {
    constructor() {
        this.currentprofile = null;

        this.add = this.add.bind(this);
        this.addFromEntry = this.addFromEntry.bind(this);
        this.initialize = this.initialize.bind(this);
        this.refresh = this.refresh.bind(this);
        this.remove = this.remove.bind(this);
        this.save = this.save.bind(this);
        this.show = this.show.bind(this);
    }

    remove(app) {
        $('#highlighted-apps-list li[data-id="' + app + '"]').remove();
    }

    add(app) {
        if (typeof app !== "string") {
            return;
        }

        if (hasSuffix(app, ".desktop") === false) {
            return;
        }

        const li = $(
            '<li></li>',
            { class: 'list-group-item', 'data-id': app, text: app }
        );
        const del = $(
            '<button></button>',
            { class: 'pull-right btn btn-danger', text: 'Delete' }
        );
        del.click(app, () => { this.remove(app) });
        del.appendTo(li);
        li.appendTo($('#highlighted-apps-list'));
    }

    refresh() {
        if (DEBUG > 0) {
            console.log('FC: Refreshing highlighted apps list');
        }
        try {
            const changes = this.currentprofile().settings["org.gnome.gsettings"];
            $.each(changes, (ignoreIndex, e) => {
                for (const key in e) {
                    if (e[key] === "/org/gnome/software/popular-overrides") {
                        try {
                            let overrides = e.value;
                            if (Array.isArray(overrides) === false) {
                                if (typeof overrides === 'string' && overrides.startsWith('[') && overrides.endsWith(']')) {
                                    const a = overrides.substring(1, overrides.length - 1);
                                    if (a.length > 0) {
                                        overrides = a.substring(1, a.length - 1).split("','");
                                    } else {
                                        overrides = null;
                                    }
                                } else {
                                    overrides = null;
                                }
                            } else {
                                overrides = null;
                            }
                            $.each(overrides, (index, value) => {
                                this.add(value);
                            });
                            return;
                        } catch (ignore) {}
                    }
                }
            });
        } catch (ignore) {}
    }

    show() {
        $('#highlighted-apps-list').html('');
        $('#profile-modal').modal('hide');
        $('#highlighted-apps-modal').modal('show');
        this.refresh();
    }

    addFromEntry() {
        clearModalFormErrors('highlighted-apps-modal');

        const app = $('#app-name').val();

        if (hasSuffix(app, ".desktop") === false) {
            messageDialog.show(
                _('Application identifier must have .desktop extension'),
                _('Invalid entry')
            );
            return;
        }
        if (app.indexOf('"') !== -1 || app.indexOf("'") !== -1) {
            messageDialog.show(
                _('Application identifier must not contain quotes'),
                _('Invalid entry')
            );
            return;
        }
        if ($('#highlighted-apps-list li[data-id="' + app + '"]').length > 0) {
            messageDialog.show(
                _('Application identifier is already in favourites'),
                _('Invalid entry')
            );
            return;
        }
        this.add(app);
        $('#app-name').val('');
    }

    save() {
        const overrides = [];
        let changed = false;
        $('#highlighted-apps-list li').each(function () {
            overrides.push($(this).attr('data-id'));
        });

        const currentprofile = this.currentprofile();
        if (currentprofile.settings["org.gnome.gsettings"] !== undefined) {
            $.each(currentprofile.settings["org.gnome.gsettings"], (ignore, e) => {
                for (const key in e) {
                    if (e[key] === "/org/gnome/software/popular-overrides") {
                        e.value = JSON.stringify(overrides).replace(/"/g, "'");
                        changed = true;
                        break;
                    }
                }
            });
            if (!changed) {
                currentprofile.settings["org.gnome.gsettings"].push({
                    key: '/org/gnome/software/popular-overrides',
                    value: JSON.stringify(overrides).replace(/"/g, "'"),
                    signature: 'as'
                });
            }
        } else {
            currentprofile.settings["org.gnome.gsettings"] = [
                {
                    key: '/org/gnome/software/popular-overrides',
                    value: JSON.stringify(overrides).replace(/"/g, "'"),
                    signature: 'as'
                }
            ];
        }
        $('#highlighted-apps-modal').modal('hide');
        $('#profile-modal').modal('show');
    }

    initialize(currentprofile_cb) {
        this.currentprofile = currentprofile_cb;
    }
}

const highlightedApp = new HighlightedApp();

export { highlightedApp };
