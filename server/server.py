#!/usr/bin/python3
#
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
# Author: Alberto Ruiz <aruiz@redhat.com>
#

import os
import json
import requests
import uuid
from flask import Flask, request, send_from_directory, render_template, jsonify

deploys = {}

collectors_by_name = {}

class GoaCollector(object):

  def __init__(self):
    self.json = {}

  def handle_change(self, request):
    self.json = dict(request.json)

  def get_settings(self):
    return self.json


class GSettingsCollector(object):

  def __init__(self):
    self.changes = {}
    self.selection = []

  def remember_selected(self, selected_indices):
    self.selection = []
    sorted_keys = sorted(self.changes.keys())
    for index in selected_indices:
      if index < len(sorted_keys):
        key = sorted_keys[index]
        change = self.changes[key]
        self.selection.append(change)

  def handle_change(self, request):
    self.changes[request.json['key']] = request.json

  def dump_changes(self):
    data = []
    for key, change in sorted(self.changes.items()):
      data.append([key, change['value']])
    return json.dumps(data)

  def get_settings(self):
    return self.selection

#Profile listing
app = Flask(__name__, template_folder="templates/")
@app.route("/profiles/", methods=["GET"])
def profile_index():
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), "index.json")

@app.route("/profiles/<path:profile_id>", methods=["GET"])
def profiles(profile_id):
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), profile_id)

@app.route("/getent", methods=['GET'])
def getent():
  #TODO: Use the python getent module to get actual users and groups
  return json.dumps({"users": ["aruiz", "mbarnes"],"groups": ["wheel", "admin", "aruiz", "mbarnes"]})

@app.route("/profile/save/<id>", methods=["POST"])
def profile_save(id):
  if id not in deploys:
    return '{"status": "nonexistinguid"}'

  form = dict(request.form)

  profile = {}
  settings = {}

  # List all keys of the form 'user-NAME', then trim off 'user-'.
  users = filter(lambda x: x.startswith('user-'), form.keys())
  users = list(map(lambda x: x[5:], users))

  # Same as above, but for 'group-NAME' keys.
  groups = filter(lambda x: x.startswith('group-'), form.keys())
  groups = list(map(lambda x: x[6:], groups))

  for name, collector in deploys[id].items():
    settings[name] = collector.get_settings()

  profile["uid"] = id
  profile["name"] = form["profile-name"][0]
  profile["description"] = form["profile-desc"][0]
  profile["settings"] = settings
  profile["applies-to"] = {"users": users, "groups": groups}
  profile["etag"] = "placeholder"

  filename = id+".json"
  index = json.loads(open('profiles/index.json').read())
  index.append({"url": filename, "displayName": form["profile-name"][0]})
  del deploys[id]

  open('profiles/' + filename, 'w+').write(json.dumps(profile))
  open('profiles/index.json', 'w+').write(json.dumps(index))

  return '{"status": "ok"}'

@app.route("/profile/delete/<url>", methods=["GET"])
def profile_delete(url):
  try:
    os.remove(os.path.join(os.getcwd(), "profiles", uid + ".json"))
  except:
    pass
  index = json.loads(open('profiles/index.json').read())
  for profile in index:
    if (profile["url"] == url):
      index.remove(profile)

  open('profiles/index.json', 'w+').write(json.dumps(index))
  return '{"status": "ok"}'

@app.route("/profile/discard/<id>", methods=["GET"])
def profile_discard(id):
  if id in deploys:
    del deploys[id]
  return '{"status": "ok"}'

#Add a configuration change to a session
@app.route("/submit_change/<name>", methods=["POST"])
def submit_change(name):
  if name in collectors_by_name:
    collectors_by_name[name].handle_change(request)
    return '{"status": "ok"}'
  else:
    return '{"status": 400}' # 400: Bad request

#Static files
@app.route("/js/<path:js>", methods=["GET"])
def js_files(js):
  return send_from_directory(os.path.join(os.getcwd(), "js"), js)


@app.route("/css/<path:css>", methods=["GET"])
def css_files(css):
  return send_from_directory(os.path.join(os.getcwd(), "css"), css)

@app.route("/img/<path:img>", methods=["GEt"])
def img_files(img):
  return send_from_directory(os.path.join(os.getcwd(), "img"), img)

#View methods
@app.route("/", methods=["GET"])
def index():
  return render_template('index.html')

@app.route("/new_profile", methods=["GET"])
def new_profile():
  return render_template('new_profile.html')

@app.route("/deploy/<uid>", methods=["GET"])
def deploy(uid):
  return render_template('deploy.html')

#profile builder methods
@app.route("/session_changes", methods=["GET"])
def session_changes():
  collector = collectors_by_name['org.gnome.gsettings']
  return collector.dump_changes()

@app.route("/session_start", methods=["GET"])
def session_start():
  collectors_by_name.clear()
  collectors_by_name['org.gnome.gsettings'] = GSettingsCollector()
  collectors_by_name['org.gnome.online-accounts'] = GoaCollector()
  req = requests.get("http://localhost:8182/start_session")
  return req.content, req.status_code

@app.route("/session_stop", methods=["GET"])
def session_stop():
  req = requests.get("http://localhost:8182/stop_session")
  return req.content, req.status_code

@app.route("/session_select", methods=["POST"])
def session_select():
  data = dict(request.form)
  sel = []
  if not "sel[]" in data:
    return '{"status": "bad_form_data"}'
  selected_indices = [int(x) for x in data['sel[]']]
  collector = collectors_by_name['org.gnome.gsettings']
  collector.remember_selected(selected_indices)

  uid = str(uuid.uuid1().int)
  deploys[uid] = dict(collectors_by_name)
  collectors_by_name.clear()

  return json.dumps({"status": "ok", "uuid": uid})

if __name__ == "__main__":
      app.run(host="0.0.0.0", port=8181, debug=True)
