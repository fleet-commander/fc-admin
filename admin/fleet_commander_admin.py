#!/usr/bin/python
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
  from configparser import ConfigParser, ParsingError
except ImportError:
  from ConfigParser import ConfigParser, ParsingError

from flask import Flask, request, send_from_directory, render_template, jsonify

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
    if self.websockify:
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

##############################################################
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
        ("/js/<path:js>",               ["GET"],  self.js_files),
        ("/css/<path:css>",             ["GET"],  self.css_files),
        ("/img/<path:img>",             ["GET"],  self.img_files),
        ("/fonts/<path:font>",          ["GET"],  self.font_files),
        ("/",                           ["GET"],  self.index),
        ("/deploy/<uid>",               ["GET"],  self.deploy),
        ("/session/start",              ["POST"], self.session_start),
        ("/session/stop",               ["GET"],  self.session_stop),
        ("/session/select",             ["POST"], self.session_select),
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

  #FIXME: Use JSON instead of urlencoding
  def profiles_save(self, id):
      def write_and_close (path, load):
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

      form = dict(request.form)

      profile = {}
      settings = {}
      groups = []
      users = []

      for name, collector in self.current_session['changeset'].items():
        settings[name] = collector.get_settings()

      groups = [g.strip() for g in form['groups'][0].split(",")]
      users  = [u.strip() for u in form['users'][0].split(",")]
      groups = filter(None, groups)
      users  = filter(None, users)

      profile["uid"] = uid
      profile["name"] = form["profile-name"][0]
      profile["description"] = form["profile-desc"][0]
      profile["settings"] = settings
      profile["applies-to"] = {"users": users, "groups": groups}
      profile["etag"] = "placeholder"

      self.check_for_profile_index()
      index = json.loads(open(INDEX_FILE).read())
      index.append({"url": id, "displayName": form["profile-name"][0]})

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
    #FIXME: Add GOA changes summary
    #FIXME: return empty json list and 403 if there's no session
    collector = self.collectors_by_name['org.gnome.gsettings']
    return collector.dump_changes()

  #Add a configuration change to a session
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

    self.current_session = { 'host': data['host'] }
    try:
      req = requests.get("http://%s:8182/session/start" % data['host'])
    except requests.exceptions.ConnectionError:
      return '{"status": "could not connect to host"}', 403

    self.vnc_websocket.stop()
    self.vnc_websocket.target_host = data['host']
    self.vnc_websocket.target_port = 5935
    self.vnc_websocket.start()

    self.collectors_by_name.clear()
    self.collectors_by_name['org.gnome.gsettings']       = GSettingsCollector()
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

  #FIXME: Rename this to /changes/select
  #TODO: change the key from 'sel' to 'changes'
  #TODO: Handle GOA changesets
  def session_select(self):
    data = request.get_json()

    if not isinstance(data, dict):
      return '{"status": "bad JSON data"}'

    if not "sel" in data:
      return '{"status": "bad_form_data"}', 403

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

def parse_config(config_file):
  SECTION_NAME = 'admin'
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
  except IOError:
    logging.warning('Could not find configuration file %s' % config_file)
  except ParsingError:
    logging.error('There was an error parsing %s' % config_file)
    sys.exit(1)
  except:
    logging.error('There was an unknown error parsing %s' % config_file)
    raise

  if not config.has_section(SECTION_NAME):
    return args

  def config_to_dict (config):
    res = {}
    for g in config.sections():
      res[g] = {}
      for o in config.options(g):
        res[g][o] = config.get(g, o)
    return res

  config = config_to_dict(config)
  args['host'] = config[SECTION_NAME].get('host', args['host'])
  args['port'] = config[SECTION_NAME].get('port', args['port'])
  args['profiles_dir'] = config[SECTION_NAME].get('profiles_dir', args['profiles_dir'])
  args['data_dir'] = config[SECTION_NAME].get('data_dir', args['data_dir'])

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
  config = parse_config(args.configuration)
  app = AdminService (__name__, config, VncWebsocketManager())
  app.run(host=config['host'], port=config['port'], debug=True)
