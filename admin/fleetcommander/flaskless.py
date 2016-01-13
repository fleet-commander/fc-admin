# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

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
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>

import sys
import os
import re
import json
import mimetypes
import logging
import StringIO
import urllib

from traceback import format_tb
from wsgiref.simple_server import make_server
from cgi import parse_qs, escape

HTTP_RESPONSE_CODES = {
    200: 'OK',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    500: 'INTERNAL SERVER ERROR',
}


class RequestDataDict(dict):
    """
    Dictionary for request data
    """

    def __init__(self, data_string=''):
        super(RequestDataDict, self).__init__()
        if data_string != '':
            self.update(parse_qs(data_string))

    def __getitem__(self, key):
        item = super(RequestDataDict, self).__getitem__(key)
        return escape(item)


class HttpRequest(object):

    """
    WSGI Request helper class
    """

    def __init__(self, environment):
        """
        Class initialization
        """
        self._environment = environment
        self.path = environment.get('PATH_INFO', '').lstrip('/')
        self.method = environment.get('REQUEST_METHOD')

        # Host and port
        if environment.get('HTTP_HOST'):
            self.host = environment['HTTP_HOST']
        else:
            self.host = environment['SERVER_NAME']

        self.host += ':%s' % environment['SERVER_PORT']

        # Parse query string
        self.query_string = environment.get('QUERY_STRING', '')
        self.GET = RequestDataDict(self.query_string)

        # Handle request content
        self.content = ''
        if environment.get('CONTENT_LENGTH'):
            length = int(environment.get('CONTENT_LENGTH'))
            self.content = environment.get('wsgi.input').read(length)

        # Parse post data
        if self.method == 'POST':
            self.POST = RequestDataDict(self.content)
        else:
            self.POST = RequestDataDict()

    def get_json(self):
        """
        Return request data in json format
        """
        return json.loads(self.content)


class HttpResponse(object):

    """
    HTTP Response class
    """

    def __init__(self, content, status_code=200, content_type='text/plain'):
        """
        Class initialization
        """

        # TODO: Migrate to use wsgiref.headers.Headers
        self.headers = {
            'Content-type': content_type,
        }

        self.status_code = status_code
        self.content = content
        self.data = content

    def get_headers(self):
        """
        Return headers as a list of tuples
        """
        return [(header, value) for header, value in self.headers.items()]


class JSONResponse(HttpResponse):
    """
    JSON Response class
    """
    def __init__(self, content, status_code=200, content_type='application/json'):
        content = json.dumps(content)
        self.jsondata = json.loads(content)
        super(JSONResponse, self).__init__(content, status_code=status_code, content_type=content_type)


class AppRouter(object):

    """
    Class for web application routing
    """

    def __init__(self, routes=None):
        """
        Class initialization
        """
        self.routes = []

        if routes is not None:
            self.add(routes)

    def add(self, routes):
        """
        Adds routes to application router

        Routes has the following structure

        (
            pattern, # Regular expression that defines route and parameters
                     # I.E. r'^profile/(?P<name>\w+)/$'
            methods, # List of methods allowed
            handler  # Function or method
        )
        """
        if not isinstance(routes, (tuple, list)):
            routes = (routes,)
        for route in routes:
            logging.debug(
                'Adding %s route for methods %s' % (route[0], route[1]))
            pattern = re.compile(route[0])
            self.routes.append((pattern, route[1], route[2]))

    def find(self, request):
        """
        Find a suitable route for given HTTP method and path
        """
        for route in self.routes:

            matches = route[0].match(request.path)
            if matches is not None:

                # Check method
                if request.method not in route[1]:
                    return None, 405

                # Let's handle it
                return route[2], matches.groupdict()

        # No route matches given path
        return None, 404


class Flaskless(object):

    """
    Minimal flask replacement for Fleet Commander
    """

    def __init__(self, *args, **kwargs):
        """
        Class initialization
        """
        routes = kwargs.setdefault('routes', None)
        templates_dir = kwargs.setdefault('templates_dir', '.')
        static_dir = kwargs.setdefault('static_dir', '.')

        self.config = {}  # For mocking flask application configuration dict

        # Set application paths
        self.static_dir = os.path.abspath(templates_dir)
        self.templates_dir = os.path.abspath(static_dir)

        # Initialize application routes
        self.routes = AppRouter(routes)

        # Save args and kwargs for later initialization of testing clients
        self.args = args
        self.kwargs = kwargs

    def render_template(self, template, context={}):
        """
        Renders a template using given context to render it
        """
        absolute_path = os.path.join(self.templates_dir, template)

        # Open file and load contents
        fd = open(absolute_path, 'r')
        filecontents = fd.read()
        fd.close()

        return filecontents

    def serve_static(self, request, path, content_type=None, basedir=None):
        """
        Serve static files
        """
        if basedir is None:
            absolute_path = os.path.join(self.static_dir, path)
        else:
            absolute_path = os.path.join(basedir, path)

        if not os.path.exists(absolute_path):
            return HttpResponse('Not found', 404)

        if content_type is None:
            content_type, encoding = mimetypes.guess_type(absolute_path)
            if content_type is None:
                content_type = 'text/plain'

        # Open file and load contents
        fd = open(absolute_path, 'r')
        filecontents = fd.read()
        fd.close()

        # Return HTTP response
        return HttpResponse(filecontents, content_type=content_type)

    def serve_html_template(self, template, context={}):
        """
        Returns a response using an HTML template
        """
        content = self.render_template(template, context)
        return HttpResponse(content, content_type='text/html')

    def handle_request(self, request):
        """
        Handles a request and returns a response
        """
        # Routing
        handler, parms = self.routes.find(request)

        if handler is not None:
            # Execute handler
            try:
                response = handler(request, **parms)
            except:
                # On errors return internal server error 500
                response = HttpResponse(HTTP_RESPONSE_CODES[500], 500)

                # Show traceback
                e_type, e_value, tb = sys.exc_info()
                traceback = ['Traceback (most recent call last):']
                traceback += format_tb(tb)
                traceback.append('%s: %s' % (e_type.__name__, e_value))
                logging.error('\n'.join(traceback))
        else:
            response = HttpResponse(HTTP_RESPONSE_CODES.get(parms, ''), parms)

        return response

    def application(self, environ, start_response):
        """
        WSGI application method
        """
        # Create request instance
        request = HttpRequest(environ)

        response = self.handle_request(request)

        status = '%s %s' % (response.status_code,
                            HTTP_RESPONSE_CODES.get(response.status_code, ''))
        headers = response.get_headers()

        # Prepare response
        start_response(status, headers)
        return response.content

    def test_client(self, stateless=False):
        """
        Returns a test client for this application
        """
        return TestClient(self, stateless)

    def run(self, host='', port=8000, **kwargs):
        """
        Run WSGI application as standalone using wsgiref
        """
        self.port = port
        self.host = host
        self.httpd = make_server(host, port, self.application)
        logging.info('Listening on %s:%s' % (host, port))
        self.httpd.serve_forever()


class TestClient(object):

    """
    Flaskless test client class
    """

    def __init__(self, app, stateless):
        """
        Class initialization
        """
        self.app = app
        self.stateless = stateless

    def _generate_environment(self, path, method='GET', data={}, content='', content_type=None):
        """
        Generates a WSGI environment object
        """
        environment = {
            'PATH_INFO': path,
            'REQUEST_METHOD': method,
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': 8000,
            'wsgi.input': '',
        }
        if method == 'GET' and data:
            environment['QUERY_STRING'] = urllib.urlencode(data)
        elif method == 'POST' and data:
            content = urllib.urlencode(data)

        if content_type is not None:
            environment['CONTENT_TYPE'] = content_type

        environment['wsgi.input'] = StringIO.StringIO(content)
        environment['CONTENT_LENGTH'] = len(content)

        return environment

    def get_app_instance(self):
        """
        Generates a clean application instance
        """
        return self.app.__class__(*self.app.args, **self.app.kwargs)

    def get(self, path, data={}):
        """
        GET request simulation
        """
        environment = self._generate_environment(path, data=data)
        logging.info('GET -> %s' % path)
        request = HttpRequest(environment)
        if self.stateless:
            app = self.get_app_instance()
        else:
            app = self.app
        response = app.handle_request(request)
        logging.info(response.status_code, response.content)
        return response

    def post(self, path, data, content_type=None):
        """
        POST request simulation
        """
        environment = self._generate_environment(path, 'POST', {}, data, content_type)
        logging.info('POST -> %s' % path)
        request = HttpRequest(environment)
        if self.stateless:
            app = self.get_app_instance()
        else:
            app = self.app
        response = app.handle_request(request)
        logging.info(response.status_code, response.content)
        return response

    def jsonpost(self, path, data):
        """
        JSON POST request simulation
        """
        return self.post(path, data=json.dumps(data), content_type='application/json')
