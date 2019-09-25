"""
Copyright (c) 2019 Michael McCartney, Kevin McLoughlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import logging
import threading

from http.server import BaseHTTPRequestHandler


class _HivemindAbstractObject(object):
    """
    Base class for many robx objects.
    """
    def __init__(self, logger: logging.Logger = None):
        self._lock = threading.RLock() # reentrant
        self._logger = logger


    def __getattr__(self, key):
        """
        Routing utility for logging reasons
        """
        if key.startswith('log_'):
            return lambda msg: self._log(key.replace('log_', ''), msg)
        raise AttributeError(
            f'{self.__class__.__name__} has no attribute "{key}"'
        )


    @property
    def lock(self):
        return self._lock


    def _log(self, type, msg):
        if self._logger:
            getattr(self._logger, type)(msg)
        else:
            getattr(logging, type)(msg)


    def run(self):
        raise NotImplementedError("Must overload run() method")


class _HandlerBase(BaseHTTPRequestHandler):
    """
    Base class for simple JSON response utilities when communicating
    with other services.
    """

    class Error(object):
        def __init__(self, message):
            self._message = message

        @property
        def message(self):
            return self._message

    endpoint = '' # If you want to only handle a custom path 

    def write_to_response(self, data, tojson=True):
        if tojson:
            self.wfile.write(
                bytes(json.dumps(data), 'utf-8')
            )
        else:
            self.wfile.write(bytes(data, 'utf-8'))


    def log_message(self, format, *args, **kwargs):
        if hasattr(self, '_log_function'):
            self._log_function(' '.join(args))


    @property
    def data(self):
        if hasattr(self, '_data'):
            return self._data

        content_length = int(self.headers['Content-Length'])
        content = self.rfile.read(content_length)
        try:
            self._data = json.loads(content)
        except:
            logging.error('Invalid data: {}'.format(content))
            return Error('Invalid data!')

        return self._data


    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()


    def do_HEAD(self):
        self._set_headers()
