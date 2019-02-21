# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2019 Red Hat, Inc.
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

import os
import shutil
import json
import logging

# Temporary directory. Set on each test run at setUp()
TEMP_DIR = None


class SMBMock(object):

    def __init__(self, servername, service, lp, creds):
        logging.debug(
            'SMBMock: Mocking SMB at \\\\%s\\%s' % (servername, service))
        self.tempdir = TEMP_DIR
        logging.debug(
            'Using temporary directory at %s' % self.tempdir)
        self.profilesdir = os.path.join(
            self.tempdir, '%s/Policies' % servername)
        if not os.path.exists(self.profilesdir):
            os.makedirs(self.profilesdir)

    def _translate_path(self, uri):
        return os.path.join(self.tempdir, uri.replace('\\', '/'))

    def loadfile(self, furi):
        logging.debug('SMBMock: LOADFILE %s' % furi)
        path = self._translate_path(furi)
        with open(path, 'rb') as fd:
            data = fd.read()
            fd.close()
        return data

    def savefile(self, furi, data):
        logging.debug('SMBMock: SAVEFILE %s' % furi)
        path = self._translate_path(furi)
        with open(path, 'wb') as fd:
            fd.write(data)
            fd.close()
        logging.debug('SMBMock: Written %s' % path)

    def chkpath(self, duri):
        logging.debug('SMBMock: CHKPATH %s' % duri)
        path = self._translate_path(duri)
        return os.path.exists(path)

    def mkdir(self, duri):
        logging.debug('SMBMock: MKDIR %s' % duri)
        path = self._translate_path(duri)
        if not os.path.exists(path):
            os.makedirs(path)

    def set_acl(self, duri, fssd, sio):
        logging.debug('SMBMock: SETACL %s' % duri)
        path = self._translate_path(duri)
        aclpath = os.path.join(path, '__acldata__.json')
        acldata = json.dumps({
            'uri': duri,
            'sio': sio,
            'fssd': fssd.as_sddl(),
        })
        with open(aclpath, 'w') as fd:
            fd.write(acldata)
            fd.close()

    def deltree(self, duri):
        logging.debug('SMBMock: DELTREE %s' % duri)
        path = self._translate_path(duri)
        if os.path.exists(path):
            shutil.rmtree(path)

SMB = SMBMock