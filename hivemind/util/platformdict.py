from __future__ import annotations

import os
import sys
import platform

from copy import deepcopy

# -- Local Constants

kThisPlatform = platform.system()

class PlatformAwareDict(object):
    """
    The platform aware dictionary wrapper that we use to autoroute
    based on the system platform or requested one.

    This is _not_ a dict object because we want to keep the
    internals separate from one another for things like JSON
    (un)/loading.


    .. code-block:: python

        mapping = {
            'foo' : {
                'windows': 'some windows val',
                'linux' : 'some linux val'
            }
        }
        pad = PlatformAwareDict(mapping)
        print (pad['foo'])

        # Windows
        >>> some windows val

        # Linux
        >>> some linux val

    Technicaly this is recursive (but why would you need that?)

    .. warning::

        Unlike a normal dictionary object, when a key cannot be
        found, the ``PlatformAwareDict`` returns ``None``


    There is also a bonus value of "unix" to support any posix
    distros.

    .. code-block:: python

        map = PlatformAwareDict({ 'foo' : { 'unix' : 'bar' } })
        print (map['foo'])

        # On both Linux and macOS
        >>> bar

    There is also the ability to pass a platform for good measure

    .. code-block:: python

        map = PlatformAwareDict({'foo' : {'unix' : 'bar'}}, 'linux')
        print (map['foo'])

        # On _any_ platform
        >>> bar

    .. note::

        The platform names are somewhat case-sensitive. Best practice
        is to stick to lowercase always.

    .. note::

        For any mac computers, ``Darwin`` is the python-known
        platform

        .. code-block:: python

            map = { 'foo' : {
                'windows' : 1,
                'linux'   : 2,
                'darwin'  : 3  # For macOS
            } }
    """

    def __init__(self, indict: dict = {}, platform_: str = kThisPlatform):
        self._platform = platform_
        if not isinstance(indict, dict):
            raise TypeError('PlatformAwareDict requires a mapping!')
        self.__d = indict


    @property
    def platform(self) -> str:
        """
        The platform this object searches for
        :return: str
        """
        return self._platform


    def set_platform(self, platform_: str):
        """
        In the event we need to switch which platform we're working
        with, this is the spot to do it.
        :return: None
        """
        self._platform = platform_


    @property
    def is_unix(self) -> bool:
        return self._platform.lower() in ['linux', 'darwin', 'unix']


    def __get_platform_entry(self, val: dict):
        """
        Internal function used to grep for platform entries
        :param val: dict to search for a platform entry
        """
        if self.platform in val:
            val = val[self.platform]
        elif self.is_unix and any(i in val for i in ('unix', 'Unix')):
            val = val[('unix' if 'unix' in val else 'Unix')]
        else:
            val = val.get(self.platform.lower(), val)

        if isinstance(val, dict):
            return PlatformAwareDict(val, platform_=self.platform)
        return val


    def __getitem__(self, key):
        """
        Magic function to grab platform based entries if present
        :return: Variant
        """
        val = self.__d.get(key, None)
        if isinstance(val, dict):
            val = self.__get_platform_entry(val)
        return val


    def __setitem__(self, key, value):
        """
        Set the value of an item. This mirrors a classic dict
        instance
        """
        self.__d[key] = value


    def __iter__(self):
        """
        Iterate through the dictionary key, values

        .. note::

            This might need work. We may want to 
        """
        return self.__d.__iter__()


    def __str__(self) -> str:
        return self.__d.__str__()


    def __bool__(self) -> bool:
        return bool(self.__d)


    def __len__(self) -> int:
        return len(self.__d)


    def __deepcopy__(self, memo=None) -> PlatformAwareDict:
        """
        Make a deepcopy of this object
        """
        return PlatformAwareDict(
            deepcopy(self.__d),
            platform_=self.platform
        )


    @classmethod
    def quick(cls, dct: dict):
        """
        Fast way to calculate platform differences using this
        object.

        .. code-block:: python

            mapping = {
                'windows' : 'foo',
                'unix' : 'bar'
            }
            print (PlatformAwareDict.quick(mapping))

            # Windows
            >>> foo

            # Unix*
            >>> bar

        :param dct: dict
        :return: Variant
        """
        return cls({'_' : dct})['_']

    def raw(self, copy: bool=False) -> dict:
        """
        Acquire the unerlying dict object.
        :param copy: Should we perform a deepcopy on the object?
        :return: dict
        """
        return self.__d if not copy else deepcopy(self.__d)


    def update(self, mapping: dict):
        """
        Update the underlying dict
        :param mapping: key, values to update our dictionary with
        :return: None
        """
        self.__d.update(mapping)


    def items(self):
        """
        Generator passback for python utility
        """
        for k, v in self.__d.items():
            if isinstance(v, dict):
                v = self.__get_platform_entry(v)
            yield (k, v)

# Small form factor
pdict = PlatformAwareDict