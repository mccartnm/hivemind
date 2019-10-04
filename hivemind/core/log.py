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

from __future__ import absolute_import

import os
import sys
import logging

from contextlib import contextmanager

# -- Defaults and Globals
MESSAGE_FORMAT = '[%(asctime)s - %(levelname)s!tabme!]: {}%(message)s'
DATETIME_FORMAT = '%d/%m/%Y %I:%M:%S %p'
DEFAULT_HANDLER = None
FILE_HANDLER = None
VERBOSE_MODE = False
CURRENT_INDENT = 0
LOGGING_STARTED = False

class BetterFormater(logging.Formatter):

    def format(self, record):
        s = super(BetterFormater, self).format(record)
        idx = s.index('!tabme!')
        s = s.replace('!tabme!', ' ' * (31 - idx))
        return s

DEFAULT_FORMAT = BetterFormater(
    fmt=MESSAGE_FORMAT.format(''),
    datefmt=DATETIME_FORMAT
)


def is_verbose():
    """
    :return: bool if we're in a verbose command
    """
    global VERBOSE_MODE
    return VERBOSE_MODE


def start(verbose, output_file=None):
    """
    Initialize logging based on the verbosity. Augment the message
    format.
    :param verbose: bool, turn chatty things on
    :return: None
    """
    global DEFAULT_HANDLER
    global FILE_HANDLER
    global DEFAULT_FORMAT
    global VERBOSE_MODE
    global LOGGING_STARTED

    if LOGGING_STARTED:
        return
    LOGGING_STARTED = True

    VERBOSE_MODE = verbose
    level = logging.INFO if not verbose else logging.DEBUG
    if os.environ.get('ROBX_VERBOSE', '').lower() not in ('', 'off', 'none', 'no'):
        level = logging.DEBUG
        VERBOSE_MODE = True

    logger = logging.getLogger()
    logger.setLevel(level)

    DEFAULT_HANDLER = logging.StreamHandler()
    logger.addHandler(DEFAULT_HANDLER)

    if output_file:
        FILE_HANDLER = logging.FileHandler(filename=output_file)
        logger.addHandler(FILE_HANDLER)

    DEFAULT_HANDLER.setFormatter(DEFAULT_FORMAT)


@contextmanager
def log_indent():
    """
    Indent the messages using a with statemment
    """
    global DEFAULT_HANDLER
    global FILE_HANDLER
    global CURRENT_INDENT

    CURRENT_INDENT += 4
    indented_format = BetterFormater(
        fmt=MESSAGE_FORMAT.format(' '*CURRENT_INDENT),
        datefmt=DATETIME_FORMAT
    )
    DEFAULT_HANDLER.setFormatter(indented_format)
    if FILE_HANDLER is not None:
        FILE_HANDLER.setFormatter(indented_format)

    yield
    CURRENT_INDENT -= 4
    right_format = BetterFormater(
        fmt=MESSAGE_FORMAT.format(' '*CURRENT_INDENT),
        datefmt=DATETIME_FORMAT
    )
    DEFAULT_HANDLER.setFormatter(right_format)
    if FILE_HANDLER is not None:
        FILE_HANDLER.setFormatter(right_format)

