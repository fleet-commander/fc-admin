#!/usr/bin/python
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2015 Red Hat, Inc.
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

import os
import sys
import unittest

import fleet_commander_controller

class TestController(unittest.TestCase):
  cookie = "/tmp/fleet-commander-start"
  args = {
      'host': 'localhost',
      'port': 8777,
      'logger_config': '/tmp/fcl.conf'
  }

  @classmethod
  def setUpClass(cls):
    fleet_commander_controller.app.conf = cls.args
    fleet_commander_controller.app.config['TESTING'] = True
    cls.app = fleet_commander_controller.app.test_client()
    #Clear all files to avoid false positives
    cls.tearDownClass()

  @classmethod
  def tearDownClass(cls):
    f = cls.args['logger_config']
    if os.path.exists(f):
      os.remove(f)
    if os.path.exists(cls.cookie):
      os.remove(cls.cookie)

  def test_00_start(self):
    ret = self.app.get("/session/start")
    # Check if systemctl start was executed
    self.assertTrue(os.path.exists(self.cookie))
    # Check HTTP return code and content
    self.assertEqual (ret.status_code, 200)
    self.assertEqual (ret.data, '{"status": "ok"}')
    # Check that the logger_config file has the right content
    self.assertTrue(os.path.exists(self.args['logger_config']))
    f = self.args['logger_config']
    self.assertTrue(os.path.exists(f))
    data = open(f).read().strip().split('\n')
    self.assertTrue ('[logger]' in data)
    self.assertTrue ('admin_server_host = localhost' in data)

  def test_01_restart(self):
    ret = self.app.get("/session/start")
    self.assertTrue(os.path.exists(self.cookie))
    self.assertEqual (ret.status_code, 403)
    self.assertEqual (ret.data, '{"status": "already_started"}')

  def test_02_stop(self):
    ret = self.app.get("/session/stop")
    self.assertEqual(ret.status_code, 200)
    self.assertEqual(ret.data, '{"status": "stopped"}')
    self.assertFalse(os.path.exists(self.cookie))

  def test_03_restop(self):
    ret = self.app.get("/session/stop")
    self.assertFalse(os.path.exists(self.cookie))
    self.assertEqual(ret.status_code, 403)
    self.assertEqual(ret.data, '{"status": "already_stopped"}')

  def test_04_start_with_systemctl_failure(self):
    os.environ['FC_FAIL'] = "true"
    ret = self.app.get("/session/start")
    self.assertFalse(os.path.exists(self.cookie))
    self.assertEqual(ret.status_code, 403)
    self.assertEqual(ret.data, '{"status": "there was a problem starting the VNC session, check the journal"}')
    os.environ.pop('FC_FAIL')

if __name__ == '__main__':
  unittest.main()
