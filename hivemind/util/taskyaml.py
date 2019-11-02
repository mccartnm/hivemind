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

# --

Where the real power comes from! The TaskYaml is some exciting stuff
"""
from __future__ import annotations

import os
import re
import sys
import copy
import shlex
import logging
import datetime
import collections
from contextlib import contextmanager

# -- thirdparty
import yaml

# -- local
from .platformdict import pdict
from .misc import merge_dicts
from ._expressions import _VariableExpansionExpression

kProperties = 'properties'

class ExpansionError(Exception):
    """ Errors related to variable expansion """
    pass


class TaskYaml(object):
    """
    File for handling custom task controls

    This is where things get really interesting in the util world.

    .. todo::

        Exmaples...
    """

    SEARCH_REGEX = re.compile(r"\{+[^\{\n]+[^\s]\}")

    def __init__(self, name: str, data: pdict):
        self._name = name
        self._data = data

        self._load_templates() # For handling template

        self._data_deque = collections.deque()


    @classmethod
    def load(cls, path: str, chatty: bool=True) -> TaskYaml:
        """
        Load a given yaml task file

        :param path: Path to the yaml file with out config
        :param chatty: Additional debug info
        :return: TaskYaml instance.
        """
        try:
            with open(path) as f:
                d = yaml.safe_load(f.read())
                if not d.get(kProperties):
                    d[kProperties] = {}
                data = pdict(d)

        except Exception as e:
            if chatty:
                logging.error(f'{path} -> invalid YAML file')
            raise IOError(str(e))

        name = data.get('name', os.path.basename(path))
        return cls(name, data)


    @property
    def name(self) -> str:
        """
        :return: The name of this Task
        """
        return self._name


    @property
    def platform(self) -> str:
        if hasattr(self, '_active_platform'):
            return self._active_platform
        return platform.system()


    @property
    def properties(self):
        return self[kProperties]


    @property
    def hm_util_path(self):
        return os.path.dirname(os.path.abspath(__file__))


    @property
    def datetime(self):
        return datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")


    def __repr__(self):
        return '<{}({})>'.format(
            self.__class__.__name__,
            self.name
        )


    def __getitem__(self, key):
        return self._data.get(key, None)


    @contextmanager
    def overload_data(self, properties: (dict, pdict)):
        """
        Context manager to work with a temporary set of values within our
        PlatformAwareDict.

        .. note::

            This updates the TaskYaml['properties'] section

        .. code-block:: pyhton

            task = TaskYaml('./task_config.yaml')
            print (task.properties['my_key'])
            
            # Output:
            >>> old

            addon_data = {
                'my_key' : 'new!'
            }

            with task.overload_data(addon_data):
                print (task.properties['my_key'])

                # Output:
                >>> new!

            print(task.properties['my_key'])

            # Output:
            >>> old

        :param properties: The properties
        """
        self._data_deque.append(self._data)
        self._data = copy.deepcopy(self._data)

        if not self._data[kProperties]:
            self._data[kProperties] = {}

        if isinstance(properties, pdict):
            self._data[kProperties].update(properties.raw())
        else:
            self._data[kProperties].update(properties)
        yield
        self._data = self._data_deque.pop()


    @contextmanager
    def using_platform(self, platform_: str):
        """
        Context manager for working with an alternal platform
        for a given scope.

        :param platform_: Know platform to use when auto-routing
        """
        og_platform = self._data.platform[:]
        self._active_platform = platform_
        self._data.set_platform(platform_)
        yield
        self._data.set_platform(og_platform)
        del self._active_platform


    def task_environment(self, env) -> None:
        """
        Config files can have env keys set on the root to augment commands
        being processed
        :param env: mapping that we can update
        """
        if not self['env']:
            return

        for k, v in self['env'].items():

            if isinstance(v, dict):
                v = pdict.quick(v)

            # We should probably so some verification that this
            # is okay
            expanded = self.expand(v, env, rtype=type(v))

            if isinstance(v, (list, tuple)):
                expanded = os.pathsep.join(expanded)
                if k in env:
                    env[k] += os.pathsep + expanded
                else:
                    env[k] = expanded

            else:
                env[k] = expanded


    def get_method(self, mstring: str):
        """
        Obtain the method we;re looking for as well as the arguments
        we may want.

        :param mstring: The string our method command is using.

            .. code-block:: yaml

                'method my_command({foo})'

        :return: tuple(list, dict)
        """
        commands = []
        kwargs = {}

        supplied = [] # provided

        # Grep for the arguments we're supplying
        if '(' in mstring:
            fidx = mstring.index('(')
            ridx = mstring.index(')')
            found_args = mstring[fidx + 1:ridx]
            if found_args:
                found_args = found_args.split(',')
                supplied = [x.strip() for x in found_args]

            mstring = mstring[:fidx]

        for key, value in self._data.items():
            if key.startswith('m__'):

                mname = key[:key.index('(')].replace('m__', '', 1)
                if mname == mstring:
                    commands = self[key]

                    #
                    # Once we have the method, we build the final
                    # values of our arguments based on what we
                    # supplied
                    #
                    fidx = key.index('(') + 1
                    ridx = key.index(')')
                    m_required_args = key[fidx:ridx]

                    if m_required_args:
                        m_arg_names = m_required_args.split(',')
                        m_arg_names = [x.strip() for x in m_arg_names]

                    scount = len(supplied)
                    acount = len(m_arg_names)
                    if scount != acount:
                        raise RuntimeError(
                            f'Invalid number of arguments for {mstring}.'
                            f' Expected: {acount}, got: {scount}'
                        )

                    for i in range(len(supplied)):
                        kwargs[m_arg_names[i]] = self.expand(supplied[i])

        return commands, kwargs


    def add_attribute(self, key, value, global_: bool=False) -> None:
        """
        Add an attribute to the properties

        :param key: The key of this value
        :param value: The value itself
        :global_: Don't remove the variable when going out of scope
        :return: None
        """
        self._data[kProperties][key] = value
        if global_:
            for d in self._data_deque:
                d[kProperties][key] = value


    def expand(self, value: (str, list), env=None, found=None, rtype=str) -> (str, list):
        """
        The real magic.

        Resolve a value as much as possible. Use the provided environment
        or our own properties mixed with our process environment, and go
        from there.

        :param value: The value to expand.
        :param env: Possibel mapping for our expand funciton to look through
        :param found: Internal arg for detecing recursive expansion
        :param rytpe: How should we return out item? One of (list, str)
        :return: rtype
        """
        if env is None:
            env = self[kProperties]
            env.update(os.environ)

        breakout = False

        if isinstance(value, list):
            # We want to build the string one by one
            total = []
            for item in value:
                total.append(self.expand(item, env, rtype=str))
            value = total

        else:

            if value is None:
                raise ExpansionError('Cannot expand null value!')

            found_to_resolve = TaskYaml.SEARCH_REGEX.findall(value)
            for needs_resolve in found_to_resolve:
                variable = needs_resolve[1:-1]

                expressions = []
                if '|' in variable:
                    values = variable.split('|')
                    variable = values[0]
                    expressions = values[1:]


                if variable.endswith('...'):
                    if not rtype is list:
                        raise ExpansionError('"..." syntax only allowed for parsed commands')

                    breakout = True
                    variable = variable[:-3]

                if ':' in variable:

                    if variable.startswith(':raw:'):
                        #
                        # A minor raw python command
                        #
                        pre_expression = str(eval(variable[len(':raw:'):])) # Not safe...

                    else:

                        #
                        # This is for the dictionary lookup. The coolest part is
                        # we can ask for properties within properties here! 
                        #
                        keys = variable.split(':')

                        if not keys[0] in env:
                            if keys[0]:
                                raise ExpansionError(f"Unknown variable root: {keys[0]}")
                            else:
                                raise ExpansionError(f"Invalid variable root: {variable}")

                        end_value = env[keys[0]]
                        for k in keys[1:]:
                            if not isinstance(end_value, (dict, pdict)):
                                raise ExpansionError(f'Bad dictionary variable expansion for: {value}')
                            end_value = end_value[k]

                        if not isinstance(end_value, str):
                            raise ExpansionError(f'Bad dictionary variable expansion for: {value}')

                        pre_expression = end_value

                elif hasattr(self, variable):
                    # Things like platform!
                    pre_expression = getattr(self, variable)

                elif variable.upper() in env:
                    # Check for environment variables first, this lets us overload more
                    # simply.
                    pre_expression = env[variable.upper()]

                elif variable in env:
                    pre_expression = env[variable]

                else:
                    continue # We haven't found anyhting...

                if expressions:
                    for expr in expressions:
                        pre_expression = _VariableExpansionExpression.compute(
                            expr, pre_expression, self
                        )
                        pass # TODO

                value = value.replace(needs_resolve, pre_expression)

        if found is None:
            found = set()

        def _rec_expand(val):
            """
            Internal recursive expansion with (hopefuly) some cyclic
            dependency checking as well as some basic unknown warnings
            """
            still_to_resolve = set(TaskYaml.SEARCH_REGEX.findall(val))
            unknown = set()

            for sub_val in still_to_resolve:
                if sub_val in found:
                    if sub_val[1:-1] not in env:
                        logging.warning(f'Unknown property: {sub_val}')
                        unknown.add(sub_val)
                        continue
                    else:
                        raise ExpansionError(
                            f'While expanding: {val} - '
                            'Potential cyclic variable expansion detected!'
                        )

                found.add(sub_val)

            for uk in unknown:
                still_to_resolve.remove(uk)

            if still_to_resolve:
                found.add(val)
                new_value = self.expand(val, env, found=found)
                if new_value in found:
                    raise ExpansionError(
                        f'While expanding: {val} - '
                        'Potential cyclic variable expansion detected!'
                    )
                return new_value

            return val

        if isinstance(value, list):
            resolved = []
            for v in value:
                resolved.append(_rec_expand(v))
            value = resolved
        else:
            value = _rec_expand(value)

        if breakout:
            return shlex.split(value)

        if rtype is list and not isinstance(value, list):
            return [value]

        if rtype is str and not isinstance(value, str):
            raise ExpansionError('Invalid rtype for value! '
                                 f'rtype = {rtype}, value_type = {type(value)}')

        return value


    def expand_property(self, property, rtype=str) -> (str, list):
        """
        Expand a select property held within this object
        :param property: The key name of the property we want to expand
        :param rtype: see expand() for more
        """
        return self.expand(self.properties[property], rtype=rtype)


    # -- Private Interface

    def _load_templates(self):
        """
        TaskYaml components can be templated out so we don't have to start
        from scratch with each config

        :return: None
        """
        include = self['include']
        include = include or []


        if not isinstance(include, (list, tuple)):
            if isinstance(include, str):
                include = [include]
            else:
                raise TypeError('TaskYaml -> "include:" must be a list or string!')

        # All root templates pull from base
        if len(include) == 0 and self.name != 'base':
            include.insert(0, 'base')

        for template in include:
            # TODO -- get the templates set up
            break
