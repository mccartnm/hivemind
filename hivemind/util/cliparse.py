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
import uuid
import importlib
import argparse

from hivemind.util import TaskYaml, pdict, CommandParser
from hivemind.util.hivecontroller import HiveController
from hivemind.core import log

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

    log.start(args.verbose)

    # Startup attributes
    config.add_attribute('_hive_name', args.name)
    config.add_attribute('_hive_key', str(uuid.uuid4()))

    parser = CommandParser(config['init_startup_commands'], task_data=config)
    parser.compute()

    print (f'New Hive at: {os.getcwd()}{os.sep}{args.name}')
    return 0


def _new_node(args: argparse.Namespace) -> int:
    """
    Initialize a new node within this hive.
    """
    log.start(args.verbose)
    if not os.path.isfile(f'config{os.sep}hive.py'):
        print ('Not a valid hive! Cannot find hive.py')
        return 1

    config = _get_startup_config()

    node_name = args.name
    config.add_attribute('_hive_name', os.path.basename(os.getcwd()))
    config.add_attribute('_node_name', node_name.replace(' ', '_'))

    # Node Defaults
    config.add_attribute('_module_import', 'hivemind')
    config.add_attribute('_node_class', '_Node')

    if args.node_class:
        module, class_ = args.node_class.rsplit('.', 1)
        config.add_attribute('_module_import', module)
        module = importlib.import_module(module)
        class_ = getattr(module, class_).__name__
        config.add_attribute('_node_class', class_)

    parser = CommandParser(config['init_new_node'], task_data=config)
    parser.compute()

    return 0


def _dev_env(args: argparse.Namespace) -> int:
    """
    Boot the development environment for a set of nodes
    """
    if not os.path.isfile(f'config{os.sep}hive.py'):
        print ('Not a valid hive! Cannot find hive.py')
        return 1

    hive_controller = HiveController(
        os.getcwd(),
        nodes=args.node,
        verbose=args.verbose,
        root=args.no_root,
        root_only=args.root_only
    )
    hive_controller.exec_()


def build_hivemind_parser() -> argparse.ArgumentParser:
    """
    Put together the fully features parser for the hivemind suite.
    :return: parser instance ready to read through args
    """
    parser = argparse.ArgumentParser(prog='hm', description=full_description)
    parser.subparser_map = {}

    subparsers = parser.add_subparsers(help='Commands that can be run')

    def _new_subparser(*args, **kwargs) -> argparse.ArgumentParser:
        parser = subparsers.add_parser(*args, **kwargs)
        parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='Provide additional feedback')
        return parser


    # -- Project creation
    new_project = _new_subparser('new', description='Set up a new hive!')
    new_project.add_argument('name', help='The name of the new project')
    new_project.add_argument('--dir', help='The directory to place it in (cwd by default)')
    new_project.set_defaults(func=_new)
    parser.subparser_map['new'] = new_project


    # -- Node creation
    new_node = _new_subparser('create_node', description='Generate a new node within a hive')
    new_node.add_argument('name', help='The name of this node')
    new_node.add_argument('-c', '--node-class', help='A specific class of node')
    new_node.set_defaults(func=_new_node)
    parser.subparser_map['create_node'] = new_node

    # -- Development Envrionment Utility
    dev_env = _new_subparser('dev', description='Start the hive to develop and test')
    dev_env.add_argument('-n', '--node', action='append', help='Specific nodes to run with this hive')
    # dev_env.add_argument('-c', '--count', nargs='+', help='The number of node instances to start')
    dev_env.add_argument('--no-root', action='store_false', help='Don\'t enable the root controller (hook to existsing)')
    dev_env.add_argument('--root-only', action='store_true', help='Only run the root controller')
    dev_env.set_defaults(func=_dev_env)
    parser.subparser_map['dev'] = dev_env

    return parser
