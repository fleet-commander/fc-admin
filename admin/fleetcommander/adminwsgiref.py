#!/usr/bin/python
# -*- coding: utf-8 -*-
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
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>

from phial import Phial
from phial import HttpResponse


class MyTestApp(Phial):

    """
    Phial test app
    """

    def __init__(self):
        routes = [
            (r'^(?P<category>\w+)/(?P<object_id>\d+)/$', ['GET'], self.category_object),
            (r'^methodtest/$', ['GET', 'POST', 'PUT', 'DELETE'], self.methodtest),
            (r'^static/(?P<path>.+)$', ['GET'], self.static),
            (r'^$', ['GET'], self.index),
        ]

        super(MyTestApp, self).__init__(routes=routes)

    def index(self, request):
        return HttpResponse('Index page')

    def category_object(self, request, category, object_id):
        return HttpResponse('Category: %s\nID: %s' % (category, object_id))

    def static(self, request, path):
        return self.serve_static(request, path)

    def methodtest(self, request):
        return HttpResponse("""
                <html>
                    <head>
                        <title>Method test</title>
                        <style>
                            form {
                                display: inline-block;
                            }
                        </style>
                    </head>
                    <body>
                        <h1>Phial test application</h1>
                        <h2>Method test</h2>
                        <form method="get">
                            <input type="hidden" name="formfield1" value="formfield1_data1">
                            <input type="hidden" name="formfield2" value="formfield1_data2">
                            <input type="hidden" name="formfield3" value="formfield1_data3">
                            <input type="submit" value="Test GET">
                        </form>
                        <form method="post">
                            <input type="hidden" name="formfield1" value="formfield1_data1">
                            <input type="hidden" name="formfield2" value="formfield1_data2">
                            <input type="hidden" name="formfield3" value="formfield1_data3">
                            <input type="submit" value="Test POST">
                        </form>
                        <h2>Request contents</h2>
                        <pre>
                            %s
                        </pre>
                        <h2>Request data</h2>
                        <h3>GET</h3>
                        <pre>
                            %s
                        </pre>
                        <h3>POST</h3>
                        <pre>
                            %s
                        </pre>

                    </body>
                </html>
            """ % (request.content, request.GET, request.POST),
            mimetype="text/html")


app = MyTestApp()
mocker = app.test_client()

tests = [
    ('/',            'GET', {}, 200, 'Index page', None),
    ('/category/1/', 'GET', {}, 200, None, None),
    ('/methodtest/', 'GET', {}, 200, None, None),
    ('/methodtest/', 'GET', {'parm1': 'value1', 'parm2': 'value2'}, 200, None, None),
    ('/methodtest/', 'POST', {'parm1': 'value1', 'parm2': 'value2'}, 200, None, None),
]

for url, method, data, expected_status, expected_output, callback in tests:
    if method == 'GET':
        response = mocker.get(url, data)
    elif method == 'POST':
        response = mocker.post(url, data)
    print '%s --> %s - Status: %s\n%s' % (method, url, response.status_code, response.content)
    assert response.status_code == expected_status
    if expected_output is not None:
        assert response.content == expected_output
    if callback is not None:
        assert callback(response) == True

print "All tests passed. Running application"
app.run()
