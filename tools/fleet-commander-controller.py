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

import subprocess
import os
import time
import signal
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

from flask import Flask

class VncSessionManager:
  service = "fleet-commander-vnc-session.service"
  def __init__(self):
    pass

  def start(self):
    ret = subprocess.Popen("systemctl start %s" % self.service, shell=True).wait()
    
    if ret != 0:
      return False
    return True

  def stop(self):
    ret = subprocess.Popen("systemctl stop %s" % self.service, shell=True)


app = Flask(__name__)
vnc = VncSessionManager()
has_session = False
STDPORT = 5935

@app.route("/vnc/port", methods=["GET"])
def vnc_address():
  return '{"port": %d}' % STDPORT, 200

@app.route("/session/start", methods=["GET"])
def new_session():
  global has_session
  global vnc

  if has_session:
    return '{"status": "already_started"}', 403

  if not vnc.start():
    return '{"status": "there was a problem starting the VNC session, check the journal"}', 403

  has_session = True
  return '{"status": "ok"}', 200

@app.route("/session/stop")
def stop_session():
  global has_session
  global vnc

  if not has_session:
    return '{"status": "already_stopped"}', 403

  vnc.stop()

  has_session = False
  return '{"status": "stopped"}', 200

def parse_config(config_file):
  SECTION_NAME = 'controller'
  args = {
      'host': '0.0.0.0',
      'port': 8182
  }

  if not config_file:
    return args

  if not os.path.exists(config_file):
    logging.warning('Could not find configuration file %s' % config_file)
    sys.exit(1)

  config = ConfigParser()
  try:
    config.read(config_file)
    config[SECTION_NAME]  
  except ParsingError:
    logging.error('There was an error parsing %s' % config_file)
    sys.exit(1)
  except KeyError:
    logging.error('Configuration file %s has no "%s" section' % (config_file, SECTION_NAME))
    return args
  except:
    logging.error('There was an unknown error parsing %s' % config_file)
    sys.exit(1)

  args['host'] = config[SECTION_NAME].get('host', args['host'])
  args['port'] = config[SECTION_NAME].get('port', args['port'])

  try:
    args['port'] = int(args['port'])
  except ValueError:
    logging.error("Error reading configuration at %s: 'port' option must be an integer value")
    sys.exit(1)

  return args

if __name__ == '__main__':
  parser = ArgumentParser(description='Admin interface server')
  parser.add_argument(
    '--configuration', action='store', metavar='CONFIGFILE', default=None,
    help='Provide a configuration file path for the web service')

  args = parser.parse_args()
  conf = parse_config(args.configuration)
  app.run(host=conf['host'], port=conf['port'], debug=True)
