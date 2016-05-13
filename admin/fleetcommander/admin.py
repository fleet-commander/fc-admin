# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

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
import re
import json
import uuid
import logging

# Fleet commander imports
from collectors import GoaCollector, GSettingsCollector, LibreOfficeCollector
from flaskless import Flaskless, HttpResponse, JSONResponse, HTTP_RESPONSE_CODES
import fcdbus
from database import DBManager

class AdminService(Flaskless):

    def __init__(self, name, config, *args, **kwargs):

        kwargs['routes'] = [
            (r'^clientdata/(?P<path>.+)$',          ['GET'],            self.serve_clientdata),
            (r'^static/(?P<path>.+)$',              ['GET'],            self.serve_static),
            ('^profiles/$',                         ['GET'],            self.profiles),
            ('^profiles/livesession$',              ['GET'],            self.profiles_livesession),
            ('^profiles/new$',                      ['POST'],           self.profiles_new),
            ('^profiles/applies/(?P<uid>[-\w\.]+)$',['GET'],            self.profiles_applies),
            ('^profiles/applies$',                  ['GET'],            self.profiles_applies),
            ('^profiles/props/(?P<uid>[-\w\.]+)$',  ['POST'],           self.profiles_props),
            ('^profiles/delete/(?P<uid>[-\w\.]+)$', ['GET'],            self.profiles_delete),
            ('^profiles/(?P<uid>[-\w\.]+)$',        ['GET'],            self.profiles_id),
            ('^profiles/apps/(?P<uid>[-\w\.]+)$',   ['POST'],           self.profiles_apps),
            ('^changes/submit/(?P<name>[-\w\.]+)$', ['POST'],           self.changes_submit_name),
            ('^changes/select$',                    ['POST'],           self.changes_select),
            ('^changes$',                           ['GET'],            self.changes),
            ('^deploy/(?P<uid>[-\w\.]+)$',          ['GET'],            self.deploy),
            ('^session/start$',                     ['POST'],           self.session_start),
            ('^session/stop$',                      ['GET'],            self.session_stop),
            ('^session/save$',                      ['POST'],           self.session_save),
            ('^hypervisor/domains/list/$',          ['GET'],            self.domains_list),
            ('^hypervisor/$',                       ['GET', 'POST'],    self.hypervisor_config),
            ('^init/$',                             ['GET'],            self.webapp_init),
            ('^$',                                  ['GET'],            self.index),
        ]
        super(AdminService, self).__init__(name, config, *args, **kwargs)

        self.DNULL = open('/dev/null', 'w')
        self.websockify_command_template = 'websockify %s:%d %s:%d'

        # Initialize database
        self.db = DBManager(config['database_path'])

        # Initialize collectors
        self.collectors_by_name = {
            'org.gnome.gsettings': GSettingsCollector(self.db),
            'org.gnome.online-accounts': GoaCollector(),
            'org.libreoffice.registry': LibreOfficeCollector(self.db),
        }

        self.current_session = self.db.config
        self.custom_args = config

        # Application data dir
        self.static_dir = os.path.join(config['data_dir'], 'static')
        self.templates_dir = os.path.join(config['data_dir'], 'templates')

        # Application state dir
        self.state_dir = config['state_dir']


    def check_for_profile_index(self):
        INDEX_FILE = os.path.join(self.custom_args['profiles_dir'], 'index.json')
        self.test_and_create_file (INDEX_FILE, [])

    def check_for_applies(self):
        APPLIES_FILE = os.path.join(self.custom_args['profiles_dir'], 'applies.json')
        self.test_and_create_file (APPLIES_FILE, {})

    def write_and_close(self, path, load):
        f = open(path, 'w+')
        f.write(load)
        f.close()

    def test_and_create_file (self, filename, content):
        if os.path.isfile(filename):
            return

        try:
            open(filename, 'w+').write(json.dumps(content))
        except OSError:
            logging.error('There was an error attempting to write on %s' % filename)

    # Views
    def index(self, request):
        return self.serve_html_template('index.html')

    def profiles_livesession(self, request):
        return self.serve_html_template('profiles.livesession.html')

    def webapp_init(self, request):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            return JSONResponse({'needcfg': c.check_needs_configuration()})
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

    def hypervisor_config(self, request):
        c = fcdbus.FleetCommanderDbusClient()

        if request.method == 'GET':
            try:
                data = c.get_hypervisor_config()
                return JSONResponse(data)
            except Exception as e:
                logging.error(e)
                return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        elif request.method == 'POST':
            data = request.get_json()
            resp = c.set_hypervisor_config(data)
            if not resp['status']:
                return JSONResponse({'errors': resp['errors']})
            return JSONResponse({})
        else:
            # This should never happen because flaskless should did this before us
            return HttpResponse(HTTP_RESPONSE_CODES[405], status_code=405)

    def domains_list(self, request):
        if 'domains' not in self.current_session:
            c = fcdbus.FleetCommanderDbusClient()
            try:
                response = c.list_domains()
            except Exception as e:
                logging.error(e)
                return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

            if response['status']:
                domains = response['domains']
            else:
                return JSONResponse({'status': 'Error retrieving domains'}, 520)
        else:
            domains = self.current_session['domains']
        return JSONResponse({'domains': domains})

    def serve_clientdata(self, request, path):
        """
        Serve client data
        """
        return self.serve_static(request, path, basedir=self.custom_args['profiles_dir'])

    def profiles(self, request):
        self.check_for_profile_index()
        return self.serve_static(request, 'index.json', basedir=self.custom_args['profiles_dir'])

    def profiles_new(self, request):
        c = fcdbus.FleetCommanderDbusClient()
        data = request.get_json()

        if not isinstance(data, dict):
            return JSONResponse({'status': 'JSON request is not an object'}, 400)
        if not all([key in data for key in ['profile-name', 'profile-desc', 'groups', 'users']]):
            # TODO: return which fields were empty
            return JSONResponse({'status': 'Missing key(s) in profile settings request JSON object'}, 400)

        try:
            resp = c.new_profile(data)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({'status': 'ok', 'uid': resp['uid']})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    def profiles_applies(self, request, uid=None):
        self.check_for_applies()
        if uid is not None:
            APPLIES_FILE = os.path.join(self.custom_args['profiles_dir'], 'applies.json')
            applies = json.loads(open(APPLIES_FILE).read())
            if uid in applies:
                return JSONResponse(applies[uid])
            else:
                return JSONResponse({"users": [], "groups": []})
        else:
            return self.serve_static(request, 'applies.json', basedir=self.custom_args['profiles_dir'])

    def profiles_props(self, request, uid):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.profile_props(request.get_json(), uid)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({'status': 'ok'})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    def profiles_id(self, request, uid):
        return self.serve_static(request, uid + '.json', basedir=self.custom_args['profiles_dir'])

    def profiles_apps(self, request, uid):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.highlighted_apps(request.get_json(), uid)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({'status': 'ok'})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    def profiles_add(self, request):
        return self.serve_html_template('profile.add.html')

    def profiles_delete(self, request, uid):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.delete_profile(uid)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({'status': 'ok'})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    def changes(self, request):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.get_changes()
            return JSONResponse(resp)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

    def changes_select(self, request):
        data = request.get_json()

        if not isinstance(data, dict):
            return JSONResponse({"status": "bad JSON data"}, 400)

        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.select_changes(data)
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({"status": "ok"})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    # Add a configuration change to a session
    def changes_submit_name(self, request, name):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.submit_change(name, request.get_json())
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if resp['status']:
            return JSONResponse({"status": "ok"})
        else:
            return JSONResponse({'status': resp['error']}, 520)

    def deploy(self, request, uid):
        return self.serve_html_template('deploy.html')

    def session_start(self, request):
        data = request.get_json()

        if not data or 'domain' not in data or 'admin_host' not in data or 'admin_port' not in data:
            return JSONResponse({"status": "Invalid data received"}, 400)

        c = fcdbus.FleetCommanderDbusClient()
        try:
            response = c.session_start(data['domain'], data['admin_host'], str(data['admin_port']))
        except:
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if not response['status']:
            return JSONResponse({'status': 'Error starting session'}, 520)

        return JSONResponse({'port': response['port']})

    def session_stop(self, request):
        c = fcdbus.FleetCommanderDbusClient()
        try:
            response = c.session_stop()
        except Exception as e:
            logging.error(e)
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if not response['status']:
            return JSONResponse({'status': 'Error stopping session'}, 520)

        return JSONResponse({})

    def session_save(self, request):

        data = request.get_json()

        if not isinstance(data, dict):
            return JSONResponse({"status": "JSON request is not an object"}, 403)
        if 'uid' not in data:
            return JSONResponse({"status": "missing key(s) in profile settings request JSON object"}, 403)

        uid = data['uid']

        if not uid:
            return JSONResponse({"status": "nonexistinguid"}, 403)

        c = fcdbus.FleetCommanderDbusClient()
        try:
            resp = c.session_save(uid)
        except:
            return JSONResponse({'status': 'Failed to connect to dbus service'}, 520)

        if not resp['status']:
            return JSONResponse({'status': resp['error']}, 520)

        return JSONResponse({'status': 'ok'})

if __name__ == '__main__':

    from argparse import ArgumentParser
    from utils import parse_config

    parser = ArgumentParser(description='Admin interface server')
    parser.add_argument(
        'host', action='store', metavar='HOST',
        help='Web service listening host')
    parser.add_argument(
        '--configuration', action='store', metavar='CONFIGFILE', default=None,
        help='Provide a configuration file path for the web service')
    parser.add_argument(
        '--port', action='store', metavar='PORT', type=int, default=None,
        help='Web service listening port')

    args = parser.parse_args()
    config = parse_config(args.configuration, args.host, args.port)
    app = AdminService(__name__, config)

    if args.host in ['localhost', '127.0.0.1']:
        print('WARNING: Running fleet commander admin listening at localhost \
                will prevent any external hosts to be able to talk to the \
                service and the Live Session feature will not work.')

    print('Fleet commander admin listening on http://%s:%s' % (config['host'], config['port']))
    print('   Static data at %s' % config['data_dir'])
    print('   Storing data at %s' % config['state_dir'])
    app.run(host=config['host'], port=config['port'], debug=True)
