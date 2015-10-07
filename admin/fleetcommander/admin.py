#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the licence, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>


# Python imports
import os
import json
import requests
import uuid
import logging

# External library imports
from flask import Flask, request, send_from_directory, render_template

# Fleet commander imports
from collectors import GoaCollector, GSettingsCollector


class AdminService(Flask):

    def __init__(self, name, config, vnc_websocket):
        super(AdminService, self).__init__(name)
        self.vnc_websocket = vnc_websocket
        self.collectors_by_name = {}
        self.current_session = {}

        routes = [
            ("/profiles/",                  ["GET"],  self.profiles),
            ("/profiles/<path:profile_id>", ["GET"],  self.profiles_id),
            ("/profiles/save/<id>",         ["POST"], self.profiles_save),
            ("/profiles/add",               ["GET"],  self.profiles_add),
            ("/profiles/delete/<uid>",      ["GET"],  self.profiles_delete),
            ("/profiles/discard/<id>",      ["GET"],  self.profiles_discard),
            ("/changes",                    ["GET"],  self.changes),
            ("/changes/submit/<name>",      ["POST"], self.changes_submit_name),
            ("/changes/select",             ["POST"], self.changes_select),
            ("/js/<path:js>",               ["GET"],  self.js_files),
            ("/css/<path:css>",             ["GET"],  self.css_files),
            ("/img/<path:img>",             ["GET"],  self.img_files),
            ("/fonts/<path:font>",          ["GET"],  self.font_files),
            ("/",                           ["GET"],  self.index),
            ("/deploy/<uid>",               ["GET"],  self.deploy),
            ("/session/start",              ["POST"], self.session_start),
            ("/session/stop",               ["GET"],  self.session_stop),
            # workaround for bootstrap font path
            ("/components/bootstrap/dist/font", ["GET"], self.font_files),
        ]
        for route in routes:
            self.route(route[0], methods=route[1])(route[2])

        self.custom_args = config
        self.template_folder = os.path.join(config['data_dir'], 'templates')

    def profiles(self):
        self.check_for_profile_index()
        return send_from_directory(self.custom_args['profiles_dir'], "index.json")

    def profiles_id(self, profile_id):
        return send_from_directory(self.custom_args['profiles_dir'], profile_id + '.json')

    def profiles_save(self, id):
        def write_and_close(path, load):
            f = open(path, 'w+')
            f.write(load)
            f.close()

        changeset = self.current_session.get('changeset', None)
        uid = self.current_session.get('uid', None)

        if not uid or uid != id:
            return '{"status": "nonexistinguid"}', 403
        if not changeset:
            return '{"status"}: "/changes/select/ change selection has not been submitted yet in the current session"}', 403

        INDEX_FILE = os.path.join(self.custom_args['profiles_dir'], 'index.json')
        PROFILE_FILE = os.path.join(self.custom_args['profiles_dir'], id+'.json')

        data = request.get_json()

        if not isinstance(data, dict):
            return '{"status": "JSON request is not an object"}', 403
        if not all([key in data for key in ['profile-name', 'profile-desc', 'groups', 'users']]):
            return '{"status": "missing key(s) in profile settings request JSON object"}', 403

        profile = {}
        settings = {}
        groups = []
        users = []

        for name, collector in self.current_session['changeset'].items():
            settings[name] = collector.get_settings()

        groups = [g.strip() for g in data['groups'].split(",")]
        users = [u.strip() for u in data['users'].split(",")]
        groups = filter(None, groups)
        users = filter(None, users)

        profile["uid"] = uid
        profile["name"] = data["profile-name"]
        profile["description"] = data["profile-desc"]
        profile["settings"] = settings
        profile["applies-to"] = {"users": users, "groups": groups}
        profile["etag"] = "placeholder"

        self.check_for_profile_index()
        index = json.loads(open(INDEX_FILE).read())
        index.append({"url": id, "displayName": data["profile-name"]})

        del(self.current_session["uid"])
        del(self.current_session["changeset"])
        self.collectors_by_name.clear()

        write_and_close(PROFILE_FILE, json.dumps(profile))
        write_and_close(INDEX_FILE, json.dumps(index))

        return '{"status": "ok"}'

    def profiles_add(self):
        return render_template('profile.add.html')

    def profiles_delete(self, uid):
        INDEX_FILE = os.path.join(self.custom_args['profiles_dir'], 'index.json')
        PROFILE_FILE = os.path.join(self.custom_args['profiles_dir'], uid+'.json')

        try:
            os.remove(PROFILE_FILE)
        except:
            pass

        index = json.loads(open(INDEX_FILE).read())
        for profile in index:
            if (profile["url"] == uid):
                index.remove(profile)

        open(INDEX_FILE, 'w+').write(json.dumps(index))
        return '{"status": "ok"}'

    def profiles_discard(self, id):
        if self.current_session.get('uid', None) == id:
            del(self.current_session["uid"])
            del(self.current_session["changeset"])
            return '{"status": "ok"}', 200
        return '{"status": "profile %s not found"}' % id, 403

    def changes(self):
        # FIXME: Add GOA changes summary
        collector = self.collectors_by_name.get('org.gnome.gsettings', None)
        if collector:
            return collector.dump_changes(), 200
        return json.dumps([]), 403

    # TODO: change the key from 'sel' to 'changes'
    # TODO: Handle GOA changesets
    def changes_select(self):
        data = request.get_json()

        if not isinstance(data, dict):
            return '{"status": "bad JSON data"}', 403

        if "sel" not in data:
            return '{"status": "bad_form_data"}', 403

        if 'org.gnome.gsettings' not in self.collectors_by_name:
            return '{"status": "session was not started"}', 403

        selected_indices = [int(x) for x in data['sel']]
        collector = self.collectors_by_name['org.gnome.gsettings']
        collector.remember_selected(selected_indices)

        uid = str(uuid.uuid1().int)
        self.current_session['uid'] = uid
        self.current_session['changeset'] = dict(self.collectors_by_name)
        self.collectors_by_name.clear()

        return json.dumps({"status": "ok", "uuid": uid})

    def check_for_profile_index(self):
        INDEX_FILE = os.path.join(self.custom_args['profiles_dir'], "index.json")
        if os.path.isfile(INDEX_FILE):
            return

        try:
            open(INDEX_FILE, 'w+').write(json.dumps([]))
        except OSError:
            logging.error('There was an error attempting to write on %s' % INDEX_FILE)

    # Add a configuration change to a session
    def changes_submit_name(self, name):
        if name in self.collectors_by_name:
            self.collectors_by_name[name].handle_change(request)
            return '{"status": "ok"}'
        else:
            return '{"status": "namespace %s not supported or session not started"}' % name, 403

    def js_files(self, js):
        return send_from_directory(os.path.join(self.custom_args['data_dir'], "js"), js)

    def css_files(self, css):
        return send_from_directory(os.path.join(self.custom_args['data_dir'], "css"), css)

    def img_files(self, img):
        return send_from_directory(os.path.join(self.custom_args['data_dir'], "img"), img)

    def font_files(self, font):
        return send_from_directory(os.path.join(self.custom_args['data_dir'], "fonts"), font)

    def index(self):
        return render_template('index.html')

    def deploy(self, uid):
        return render_template('deploy.html')

    def session_start(self):
        data = request.get_json()
        req = None

        if self.current_session.get('host', None):
            return '{"status": "session already started"}', 403

        if not data:
            return '{"status": "Request data was not a valid JSON object"}', 403

        if 'host' not in data:
            return '{"status": "no host was specified in POST request"}', 403

        self.current_session = {'host': data['host']}
        try:
            req = requests.get("http://%s:8182/session/start" % data['host'])
        except requests.exceptions.ConnectionError:
            return '{"status": "could not connect to host"}', 403

        self.vnc_websocket.stop()
        self.vnc_websocket.target_host = data['host']
        self.vnc_websocket.target_port = 5935
        self.vnc_websocket.start()

        self.collectors_by_name.clear()
        self.collectors_by_name['org.gnome.gsettings'] = GSettingsCollector()
        self.collectors_by_name['org.gnome.online-accounts'] = GoaCollector()

        return req.content, req.status_code

    def session_stop(self):
        host = self.current_session.get('host', None)

        if not host:
            return '{"status": "there was no session started"}', 403

        msg, status = ('{"status": "could not connect to host"}', 403)
        try:
            req = requests.get("http://%s:8182/session/stop" % host)
            msg, status = (req.content, req.status_code)
        except requests.exceptions.ConnectionError:
            pass

        self.vnc_websocket.stop()
        self.collectors_by_name.clear()

        if host:
            del(self.current_session['host'])

        return msg, status
