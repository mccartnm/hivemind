
import json
import logging
import threading

from http.server import BaseHTTPRequestHandler


class _RobXObject(object):
    """
    Base class for many robx objects.
    """
    def __init__(self):
        self._lock = threading.RLock() # reentrant


    @property
    def lock(self):
        return self._lock


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

    def write_to_response(self, data):
        self.wfile.write(
            bytes(json.dumps(data, indent=4), 'utf-8')
        )


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
