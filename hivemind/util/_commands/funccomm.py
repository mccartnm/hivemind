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

Function and compute related commands
"""
import os
import sys
import glob
import shutil
import logging
import fnmatch

from argparse import ArgumentParser, REMAINDER

from .comm import _AbstractCommand, CommandError, T, ComputeReturn


class MethodComm(_AbstractCommand):
    """
    Command to execute a function within our TamlYaml instance
    """
    name = 'method'

    def description(self) -> str:
        return 'Execute a known function within our TaskYaml'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'call',
            help='The function to execute with parameters',
            nargs=REMAINDER
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        from hivemind.util.commparse import CommandParser
        method_string = ''.join(self.data.call)

        # Go find the function.
        commands, args = task_data.get_method(method_string)

        if not commands:
            # TODO: Use levenshtien to get closes function name
            raise CommandError(
                f'No function named: "{method_string}".'
            )

        parser = CommandParser(
            commands,
            task_data,
            args
        )
        parser.compute()


class FailureComm(_AbstractCommand):
    """
    If we get here, make sure we stop now!
    """
    name = 'fail'

    def description(self) -> str:
        return 'Stop all command processing and exit with a message'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'text',
            nargs='+',
            help='Text that we\'ll display with the failure'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        raise CommandError(' '.join(self.data.text))


class ReturnComm(_AbstractCommand):
    """
    Return command to jump out of the current scope
    """
    name = 'return'

    def description(self) -> str:
        return 'Return from the current scope'


    def populate_parser(self, parser: ArgumentParser) -> None:
        """
        Currently we don't have any arguments. Perhaps one day
        we can look into value returns
        """
        return


    def exec_(self, task_data: T) -> ComputeReturn:
        return _AbstractCommand.RETURN_