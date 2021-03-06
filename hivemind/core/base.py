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

from typing import Any, Union

from aiohttp import web

class _HivemindAbstractObject(object):
    """
    Base class for many robx objects.
    """
    def __init__(self, logger: logging.Logger = None):
        self._lock = threading.RLock() # reentrant
        self._logger = logger


    def __getattr__(self, key) -> Any:
        """
        Routing utility for logging reasons. See
        _HivemindAbstractObject._log() for more information
        :return: Any
        """
        if key.startswith('log_'):
            return lambda msg: self._log(key.replace('log_', ''), msg)
        raise AttributeError(
            f'{self.__class__.__name__} has no attribute "{key}"'
        )


    @property
    def lock(self) -> threading.RLock:
        """
        All hive objects contain an internal threading.RLock for whatever
        use case the developer can think of.

        :return: The threading.RLock() given to this object.
        """
        return self._lock


    @property
    def logger(self) -> Union[logging.Logger, None]:
        """ :return: The logger assigned to this object or None """
        return self._logger


    def _log(self, type: str, msg: str) -> None:
        """
        Execute a specific log function. This works by using getattr
        to obtain the function from our logger. If no logger is set on
        the object, the default is used.

        :param type: The logger attribute (one of ingo, debug, warning, error,
                     critical)
        :param msg: The message to relay
        :return: None
        """
        if self._logger:
            getattr(self._logger, type)(msg)
        else:
            getattr(logging, type)(msg)


    def run(self):
        """
        The function that all hive objects should overload to execute whatever
        their specific process is.
        """
        raise NotImplementedError("Must overload run() method") # pragma: no cover


class _HandlerBase:
    """
    Base class for simple JSON response utilities when communicating
    with other services.
    """
    def __init__(self) -> None:
        pass

    class Error(object): # pragma: no cover
        def __init__(self, message):
            self._message = message

        @property
        def message(self):
            return self._message

    endpoint = '' # If you want to only handle a custom path 

    def log_message(self, format, *args, **kwargs):
        if hasattr(self, '_log_function'):
            self._log_function(' '.join(args))
