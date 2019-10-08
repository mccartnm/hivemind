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
from __future__ import annotations

import os
import re
import sys
import shlex
import logging

from typing import Union, TypeVar

from ..core import log
from ._commands.comm import _AbstractCommand, ComputeReturn

# -- Type to describe the TaskYaml class

T = TypeVar('TaskYaml')

# -- Specific Types

CommandTypes = Union[str, list, dict]


class ComputeError(Exception):
    """ Exception related to the command execution """
    pass


class CommandParser(object):
    """
    Parse utility for commands that we wish to run. This contains a
    TaskYaml instance to make it possible to use variable expansion
    and host a few powerful utilities.
    """
    HM_COMMAND = re.compile(r'^\:(?P<name>[^\s]+)(\s)?(?P<args>(.*))$')

    def __init__(self, commands: CommandTypes, task_data: T, arguments: dict = {}) -> None:

        self._commands = commands
        self._task_data = task_data
        self._arguments = arguments


    def compute(self) -> None:
        """
        Execute the commands supplied to this object
        :return: None
        """
        with self._task_data.overload_data(self._arguments):
            self._compute(self._commands)

    # -- Private Interface

    def _compute(self, commands: CommandTypes) -> ComputeReturn:
        """
        Internal compute call to help with building our tools. This
        will iterate through lists, handle conditional maps, and
        process the strings holding onto actual command processes

        :param commands: (str|dict) of commands to process
        :return: (str|None)
        """
        if isinstance(commands, list):
            for command in commands:
                if self._compute(command) == _AbstractCommand.RETURN_:
                    return _AbstractCommand.RETURN_

        elif isinstance(commands, dict):
            # Conditional execution

            if 'for' in commands:

                if not 'than' in commands:
                    raise ComputeError(
                        '"than" commands required for conditional commands'
                    )

                # We have an iteration
                for_options = commands['for'].split(' ')
                for_options = list(filter(lambda x: x != '', for_options))

                if not len(for_options) == 3:
                    raise ComputeError(
                        'for loop requires three arguments'
                    )

                param_name, _, property_name = for_options
                iterable = self._task_data.properties[property_name[1:-1]]

                for item in iterable:
                    with self._task_data.overload_data({param_name:item}):
                        self._compute(commands['than'])

            else:

                if not 'if' in commands:
                    raise ComputeError(
                        "'if' required for conditional commands"
                    )

                if not 'than' in commands:
                    raise ComputeError(
                        "'than' commands required from conditional commands"
                    )

                if self._evaulate(commands['if']):
                    self._compute(commands['than'])
                elif 'else' in commands:
                    self._compute(commands['else'])

                # Should we add elif1, elif2, etc?

        elif isinstance(commands, str):
            # A command!

            command_instance = self._parse(commands)
            command_instance._process_args()

            logging.debug(str(command_instance))
            with log.log_indent():
                result = command_instance.exec_(self._task_data)
                if result == _AbstractCommand.RETURN_:
                    return _AbstractCommand.RETURN_

        else:
            raise ComputeError(
               f'Command, unknown type: {type(commands)}'
            )


    def _evaulate(self, expr: str) -> bool:
        """
        Evaluate a python expression and return if it's true

        :param expr: The expression to evalute
        :return: bool
        """
        # TODO: _QuickPythonExpression
        # return eval(expr, _QuickPythonExpression._registry)
        return eval(expr)


    def _parse(self, command_string: str) -> _AbstractCommand:
        """
        Given a command string, attempt to look for a known internal
        command and return an instance of the class assigned to it.

        If a raw cli command, the _AbstractCommand class is used to
        run said process.

        :param command_string: The raw command comming from our
                               TaskYaml
        :return: _AbstractCommand instance (possibly a subclass)
        """
        match = self.HM_COMMAND.match(command_string)
        if match:
            info = match.groupdict()

            raw_args = shlex.split(info['args'])
            command_class = _AbstractCommand.command(
                info['name'].lower()
            )
        else:
            raw_args = shlex.split(command_string)
            command_class = _AbstractCommand

        expanded_args = []
        for arg in raw_args:
            expanded_args.extend(
                self._task_data.expand(arg, rtype=list)
            )

        return command_class(*expanded_args)
