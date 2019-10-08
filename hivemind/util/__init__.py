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

from .platformdict import PlatformAwareDict, pdict
from .taskyaml import TaskYaml, ExpansionError
from .misc import merge_dicts, levenshtein

from ._commands.comm import _AbstractCommand, CommandError

from .commparse import CommandParser, ComputeError

from typing import Any

class _GlobalSettings(object):
    """
    Gobal settings accessed by nodes and controllers alike
    """
    def __init__(self):
        self.__d = {}


    def set(self, parameters: dict) -> None:
        for k, v, in parameters.items():
            self.__d[k] = v


    def get(self, key, default=None) -> Any:
        return self.__d.get(key, default)


    def feature_enabled(self, feature: str) -> None:
        """
        Check if a select feature has been enabled by the hive
        :param feature: The name of the feature
        :return: bool
        """
        return feature in self['hive_features']


    def __setitem__(self, key, value) -> None:
        self.__d[key] = value


    def __getitem__(self, key) -> Any:
        return self.__d[key]


    def update(self, other: dict) -> None:
        self.__d.update(other)


    def _total_reset(self):
        """
        Called to completely reset the global_settings dictionary

        .. warning::

            For internal use only. Should never be used in production

        :return: None
        """
        self.__d = {}


#
# Internal pointer object to make sure we _always_ use the same
# settings instance no matter how we import it.
#
_GlobalSettings._internal_settings_instance = _GlobalSettings()
class _GlobalSettingsHandler(object):
    def __setitem__(self, key, value):
        _GlobalSettings._internal_settings_instance.__setitem__(key, value)

    def __getitem__(self, key):
        return _GlobalSettings._internal_settings_instance.__getitem__(key)

    def __getattr__(self, key):
        return getattr(_GlobalSettings._internal_settings_instance, key)


#
# The publicly available settings tool
#
global_settings = _GlobalSettingsHandler()
