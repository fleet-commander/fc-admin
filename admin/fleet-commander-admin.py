#!/usr/bin/python3
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
# Author: Alberto Ruiz <aruiz@redhat.com>
#

import os
import json
import requests
import uuid
import logging
import sys
import subprocess

from argparse import ArgumentParser

#compat between Pyhon 2 and 3
try:
  from configparser import ConfigParser
except ImportError:
  from ConfigParser import ConfigParser

from flask import Flask, request, send_from_directory, render_template, jsonify

deploys = {}
collectors_by_name = {}
global_config = {}

class VncWebsocketManager(object):
  _COMMAND_TEMPLATE = "websockify %s:%d %s:%d"

  def __init__(self, **kwargs):
    ''' Construction arguments:
      listen_host: host to listen for WS connections
      listen_port: port to listen for WS connections
      target_host: native socket host connection
      target_port: native socket port connection
    '''
    self.listen_host = kwargs.get('listen_host', 'localhost')
    self.listen_port = kwargs.get('listen_port', 8989)
    self.target_host = kwargs.get('target_host', 'localhost')
    self.target_port = kwargs.get('target_port', 5900)
    self.websockify = None
    self.DNULL = open('/dev/null', 'w')

  def start(self):
    if self.websockify:
      return

    command = self._COMMAND_TEMPLATE % (self.listen_host, self.listen_port,
                                        self.target_host, self.target_port)

    self.websockify = subprocess.Popen(command, shell=True,
                                       stdin=self.DNULL, stdout=self.DNULL, stderr=self.DNULL)

  def stop(self):
    self.websockify.kill()
    self.websockify = None

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
app = Flask(__name__)
@app.route("/profiles/", methods=["GET"])
def profile_index():
  check_for_profile_index()
  return send_from_directory(app.custom_args['profiles_dir'], "index.json")

@app.route("/profiles/<path:profile_id>", methods=["GET"])
def profiles(profile_id):
  return send_from_directory(app.custom_args['profiles_dir'], profile_id)

@app.route("/profile/save/<id>", methods=["POST"])
def profile_save(id):
  if id not in deploys:
    return '{"status": "nonexistinguid"}'

  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], 'index.json')
  PROFILE_FILE = os.path.join(app.custom_args['profiles_dir'], id+'.json')

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

  check_for_profile_index()
  index = json.loads(open(INDEX_FILE).read())
  index.append({"url": filename, "displayName": form["profile-name"][0]})
  del deploys[id]

  open(PROFILE_FILE, 'w+').write(json.dumps(profile))
  open(INDEX_FILE, 'w+').write(json.dumps(index))

  return '{"status": "ok"}'

@app.route("/profile/delete/<uid>", methods=["GET"])
def profile_delete(uid):
  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], 'index.json')
  PROFILE_FILE = os.path.join(app.custom_args['profiles_dir'], uid+'.json')

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

@app.route("/profile/discard/<id>", methods=["GET"])
def profile_discard(id):
  if id in deploys:
    del deploys[id]
  return '{"status": "ok"}'

#Get users and groups from the target host
@app.route("/getent", methods=['GET'])
def getent():
  #TODO: Use the python getent module to get actual users and groups
  return json.dumps({"users": ["aruiz", "mbarnes"],"groups": ["wheel", "admin", "aruiz", "mbarnes"]})

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
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "js"), js)


@app.route("/css/<path:css>", methods=["GET"])
def css_files(css):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "css"), css)

@app.route("/img/<path:img>", methods=["GEt"])
def img_files(img):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "img"), img)

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

@app.route("/session/start", methods=["GET"])
def session_start():
  collectors_by_name.clear()
  collectors_by_name['org.gnome.gsettings'] = GSettingsCollector()
  collectors_by_name['org.gnome.online-accounts'] = GoaCollector()
  req = requests.get("http://localhost:8182/start_session")
  return req.content, req.status_code

@app.route("/session/stop", methods=["GET"])
def session_stop():
  req = requests.get("http://localhost:8182/stop_session")
  return req.content, req.status_code

@app.route("/session/select", methods=["POST"])
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

def check_for_profile_index():
  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], "index.json")
  if os.path.isfile(INDEX_FILE):
    return

  try:
    open(INDEX_FILE, 'w+').write(json.dumps([]))
  except OSError:
    logging.error('There was an error attempting to write on %s' % INDEX_FILE)

def parse_config(config_file):
  #TODO: Safest default for the paths?
  args = {
      'host': 'localhost',
      'port': 8181,
      'profiles_dir': os.path.join(os.getcwd(), 'profiles'),
      'data_dir': os.getcwd(),
  }

  if not config_file:
    return args

  config = ConfigParser()
  try:
    config.read(config_file)
    config["admin"]
  except FileNotFoundError:
    logging.warning('Could not find configuration file %s' % config_file)
  except configparser.ParsingError:
    logging.error('There was an error parsing %s' % config_file)
    sys.exit(1)
  except KeyError:
    logging.error('Configuration file %s has no "admin" section' % config_file)
    sys.exit(1)
  except:
    logging.error('There was an unknown error parsing %s' % config_file)
    sys.exit(1)

  args['host'] = config['admin'].get('host', args['host'])
  args['port'] = config['admin'].get('port', args['port'])
  args['profiles_dir'] = config['admin'].get('profiles_dir', args['profiles_dir'])
  args['data_dir'] = config['admin'].get('data_dir', args['data_dir'])

  try:
    args['port'] = int(args['port'])
  except ValueError:
    logging.error("Error reading configuration at %s: 'port' option must be an integer value")
    sys.exit(1)

  return args

if __name__ == "__main__":
  parser = ArgumentParser(description='Admin interface server')
  parser.add_argument(
    '--configuration', action='store', metavar='CONFIGFILE', default=None,
    help='Provide a configuration file path for the web service')

  args = parser.parse_args()
  app.custom_args = parse_config(args.configuration)
  app.template_folder = os.path.join(app.custom_args['data_dir'], 'templates')
  app.run(host=app.custom_args['host'], port=app.custom_args['port'], debug=True)
