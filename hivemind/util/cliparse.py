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
import argparse

from hivemind.util import TaskYaml, pdict, CommandParser

full_description = """Hivemind utility belt with quick access tools for
running task nodes, starting new projects, and more.
"""

def _get_startup_config() -> TaskYaml:
    """
    Obtain the startup configuration that contains all kinds of helpful
    utilities for hive management.
    :return: TaskYaml instance
    """
    return TaskYaml.load(
        os.path.dirname(__file__) + '/_static_config/startup.yaml'
    )


def _new(args: argparse.Namespace) -> int:
    """
    Begin a new hive! Create initial scafolding for the project, nodes,
    etc.
    :param args: The namespace that we're given with our settings
    :return: int
    """
    if args.dir:
        os.chdir(args.dir)

    config = _get_startup_config()

    # Startup attributes
    config.add_attribute('_hive_name', args.name)

    parser = CommandParser(config['init_startup_commands'], task_data=config)
    parser.compute()

    print (f'New Hive at: {os.getcwd()}{os.sep}{args.name}')
    return 0


def _new_node(args: argparse.Namespace) -> int:
    """
    Initialize a new node within this hive.
    """
    if not os.path.isfile('hive.py'):
        print ('Not a valid hive! Cannot find hive.py')
        return 1

    config = _get_startup_config()

    node_name = args.name
    config.add_attribute('_hive_name', os.path.basename(os.getcwd()))
    config.add_attribute('_node_name', node_name.replace(' ', '_'))

    parser = CommandParser(config['init_new_node'], task_data=config)
    parser.compute()

    return 0


def build_hivemind_parser() -> argparse.ArgumentParser:
    """
    Put together the fully features parser for the hivemind suite.
    :return: parser instance ready to read through args
    """
    def _populate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='Provide additional feedback')

    parser = argparse.ArgumentParser(prog='hm', description=full_description)
    subparsers = parser.add_subparsers(help='Commands that can be run')

    # -- Project creation
    new_project = subparsers.add_parser('new', description='Set up a new hive!')
    _populate_parser(new_project)
    new_project.add_argument('name', help='The name of the new project')
    new_project.add_argument('--dir', help='The directory to place it in (cwd by default)')
    new_project.set_defaults(func=_new)

    new_node = subparsers.add_parser('create_node', description='Generate a new node within a hive')
    _populate_parser(new_node)
    new_node.add_argument('name', help='The name of this node')
    new_node.set_defaults(func=_new_node)

    return parser
