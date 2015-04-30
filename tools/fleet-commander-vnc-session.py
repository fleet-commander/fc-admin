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

import subprocess
import os
import time
import signal
import uuid

from flask import Flask

class VncSessionManager:
  #GNOME_SESSION = 'DISPLAY=:10 gnome-session'

  def __init__(self):
    self.gnome_session = None

  def start(self):
    if self.gnome_sessiony:
      return False

    #DNULL = open('/dev/null', 'w')
    #self.xspice = subprocess.Popen(template % self.XSPICE, shell=True, stdout=DNULL, stderr=DNULL, stdin=DNULL)
    return True

  def stop(self):
    #NOTE: This is a brute force approach to kill all fc-user processes
    #subprocess.call ('pkill -u fc-user', shell=True)
    pass

app = Flask(__name__)

has_session = False

@app.route("/start_session", methods=["GET"])
def new_session():
  global has_session

  if has_session:
    return '{"status": "already_started"}', 403

  has_session = True
  return '{"status": "ok"}', 200

@app.route("/stop_session")
def stop_session():
  global has_session

  if not has_session:
    return '{"status": "already_stopped"}', 403

  has_session = False
  return '{"status": "stopped"}', 200

if __name__ == '__main__':  
  app.run(host='localhost', port=8182, debug=True)
