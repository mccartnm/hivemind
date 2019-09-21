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
import os
import re
import sys
import shlex
import subprocess
from typing import TypeVar, Generic

from purepy import PureVirtualMeta

T = TypeVar('TaskYaml')
_quote_scan = re.compile(r"^\"[^\"]\"^")

def run_process(command_with_args: (str, list),
                custom_env: dict = {},
                task_data: (T, None) = None) -> int:
    """
    Execute a command along with any arguments supplied. Should it fail,
    return that exit code.

    :param command_with_args: list|str of the command we're going to run
    :param custom_env: Use custom environment values
    :param task_data: optional TaskYaml instance
    :return: int exit code
    """
    env = dict(od.environ, **custom_env)
    if task_data is not None:
        task_data.task_environment(env)

    # Should this be just passed to the subprocess calls?
    os.environ.update(env)

    if not isinstance(command_with_args, (list, tuple)):
        full_command = shlex.split(command_with_args)
    else:
        full_command = list(command_with_args)

    for i, c in enumerate(full_command):
        if _quote_scan.match(c):
            full_command[i] = c[1:-1]

    return subprocess.run(command).returncode


def merge_dicts(dict1: dict, dict2: dict, combine_keys=None, ignore=None):
    """
    Merge dictionaries recursively and pass back the result. If a conflict of
    types arrive, just get out with what we can.

    :param dict1: The entry dictionary, this takes precedence when merge
                  conflicts arrive
    :param dict2: The merge-with dictionary
    :param combine_key: The keys that we should combine lists with.
        .. note::

            This is pretty temperamental.

    :param ignore: Keys to complete ignore
    """
    if combine_keys is None:
        combine_keys = {}

    if ignore is None:
        ignore = []

    def _merge_list_of_dicts(list1, list2, key):

        list1_values = [l[key] for l in list1]
        list2_values = [l[key] for l in list2]

        for v in set(list1_values).union(list2_values):
            if v in list2_values:
                # If the value is in the second list, we use that instead
                yield list2[list2_values.index(v)]
            else:
                yield list1[list1_values.index(v)]


    for k in set(dict1.keys()).union(dict2.keys()):
        if k in dict1 and k in dict2:
            if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                if k in ignore:
                    yield (k, dict2[k])
                else:
                    yield (k, dict(merge_dicts(dict1[k], dict2[k], combine_keys, ignore)))
            else:
                # If one of the values is not a dict, you can't continue merging it.
                # Value from second dict overrides one in first and we move on.

                # That is, unless, we've supplied combine keys. This is for list
                # concatinaion based on a given key.
                if k in combine_keys:
                    if isinstance(dict1[k], list) and isinstance(dict2[k], list):
                        yield (k, list(_merge_list_of_dicts(dict1[k], dict2[k], combine_keys[k])))
                    else:
                        yield (k, dict2[k])
                else:
                    yield (k, dict2[k])
        elif k in dict1:
            yield (k, dict1[k])
        else:
            yield (k, dict2[k])


def levenshtein(s1, s2):
    """
    Pythonic levenshtein math to quickly determine how many "edits" two strings are
    differently than one another.

    Code snippet by Halfdan Ingvarsson

    :param s1: String to compare
    :param s2: String to compare
    :return: int - number of edits required (higher number means more different)
    """

    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            # than s2
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


# -- Metaclasses


class SimpleRegistry(type):
    """
    A metaclass that builds a registry automatically
    """
    def __init__(cls, name, bases, dct) -> None:
        if not hasattr(cls, '_registry'):
            cls._registry = {} # Base Class
        elif cls.name:
            cls._registry[cls.name] = cls


class PV_SimpleRegistry(PureVirtualMeta, SimpleRegistry):
    """
    Metaclass that builds a registry and contains the
    purepy pure virtual functionality 
    """
    def __init__(cls, name, bases, dct) -> None:
        PureVirtualMeta.__init__(cls, name, bases, dct)
        SimpleRegistry.__init__(cls, name, bases, dct)