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
import sys
import logging
import platform

from argparse import ArgumentParser

from .comm import _AbstractCommand, CommandError, T, ComputeReturn

from ..misc import temp_dir

class SetComm(_AbstractCommand):
    """
    Set a value within our properties
    """
    name = 'set'

    def description(self) -> str:
        return 'Set a property within our task data to be ' +\
               'used at a later time'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '-g', '--global-var',
            action='store_true',
            help='Set this as a global variable no matter the scope'
        )

        parser.add_argument(
            'property',
            help='The property to set our value to'
        )

        parser.add_argument(
            'value', help='The value to set' 
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        task_data.add_attribute(
            self.data.property,
            self.data.value,
            global_=self.data.global_var
        )


class SourceCom(_AbstractCommand):
    """
    The environment of our commands is vital. We need a way to
    source external scripts to augment this environment. That's
    easier said than done - more so in a platform agnostic way
    """
    name = 'source'

    def description(self) -> str:
        return 'Source a file to modify the command environment'


    def populate_parser(self, parser: ArgumentParser) -> ComputeReturn:
        parser.add_argument(
            'script',
            help='The script to source'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        with temp_dir() as dir_:
            logging.debug(f'Sourcing Environment: {self.data.script}')
            env_text = '_environment.txt'

            if platform.system() == 'Windows':

                env_script = '_environment.bat'
                with open(env_script, 'w') as env_bat:
                    env_bat.write('@echo off\n')
                    env_bat.write(f'call {self.data.script}\n')
                    env_bat.write(f'set > {env_text}\n')

            else:

                env_script = '_environment.sh'
                with open(env_script, 'w') as env_sh:
                    env_sh.write(f'source {self.data.script}\n')
                    env_sh.write(f'env > {env_text}\n')

                # We have to use bash to call this on unix
                # because it's not in the PATH
                env_script = 'bash ./' + env_script

            os.system(env_script)
            with open(env_text, 'r') as env_read:
                lines = env_read.read().splitlines()

            for line in lines:
                var, value = line.strip().split('=', 1)
                os.environ[var] = value
