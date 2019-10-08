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
import time
import types
import platform
import asyncio
import logging
import logging.handlers
import threading
import importlib.machinery
import importlib.util
from typing import Optional
from contextlib import contextmanager

from hivemind import _Node
from hivemind.util import global_settings
from hivemind.core import log

from .crashthread import TerminalThread


class HiveError(Exception):
    """ Errors relating to the hive controller """
    pass


class HiveController(object):
    """
    Utility class for managing multiple threads under the hood.

    This treats each controller and node in a unique thread that responds in a
    similar pattern that having each on an individual process will do.

    This is a good entry point for starting and testing nodes on the network.
    Using multiple HiveControllers you can stand up the majority of your network
    and leave the nodes you're looking to develop on (a) separate hive
    controller(s)

    In a production environment, we can probably use this in a more transparent
    fashion.
    """
    def __init__(self,
                 hive_root: str,
                 nodes: list = [],
                 root: bool = True,
                 root_only: bool = False,
                 verbose: bool = False,
                 augment_settings: Optional[dict] = {}) -> None:
        """
        Initialize a Hive

        :param hive_root: The root location of a hive project
        :param nodes: list of node names that we snhould look for when starting up
        :param root: Should we boot up the root controller?
        :param verbose: Use verbose logging
        """
        if root_only:
            root = True

        self._verbose = verbose
        self._hive_root_folder = hive_root
        self._load_settings(augment_settings)

        self._root_module = None
        self._root_class = None
        self._root_instance = None
        self._root_args = []
        self._root_kwargs = {}
        if root:
            self._obtain_root_class()

        if not root_only:
            # self._node_execution_config = {}
            if not nodes:
                self._node_classes = self.__get_all_nodes()
            elif not isinstance(nodes[0], str) and issubclass(nodes[0], _Node):
                self._node_classes = nodes
            else:
                self._node_classes = self.__nodes_from_names(nodes)
        else:
            self._node_classes = []

        # -- Thread control
        self._root_thread = None
        self._node_threads = []
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        self._root_loop = None
        self._root_abort = None
        self._node_aborts = []


    @property
    def settings(self):
        return global_settings


    @contextmanager
    def async_exec_(self):
        """
        Used mainly for testing, this is a context manager that will
        start the network and hold onto it while you can use code to
        manipulate it.

        .. code-block:: python

            hive = HiveController(...)
            with hive.async_exec_():
                # The network is running, do something with it!
                # ...

        """
        self.exec_(async_=True)
        yield
        self.__kill()


    def exec_(self, timeout=None, async_=False) -> None:
        """
        Run our nodes/controllers as requested
        :return: None
        """
        try:
            # Make sure we cleanup if something goes wrong here too

            if self._root_class:
                self.__init_root()

            if self._node_classes:
                self.__init_nodes()

        except Exception as e:
            self.__kill()
            raise

        if not async_:
            try:
                if timeout is not None:
                    time.sleep(timeout)
                else: # pragma: no cover
                    # This is obviously not good enough. We need to have a means
                    # of waiting for things until the user gives some kind of signal
                    # Otherwise this will never be viable as a service
                    while True:
                        inp = input()
                        if inp == 'q':
                            raise RuntimeError('Quit')
            except KeyboardInterrupt as e:
                pass # Ignore the printing

            except Exception as err:
                raise

            finally:
                self.__kill()


    def node_logger(self, node_name: str, level: int) -> logging.Logger:
        """
        Generate a new logger for our node that specific to itself
        :param node_name: name of the _Node instance with a unique name
        :param level: logging.Level to set this item to
        :return: logging.Logger
        """
        log_location = os.path.join(global_settings['log_location'],
                                    node_name + '.log')
        return self._new_logger(node_name, log_location, level)


    def root_logger(self, level: int) -> logging.Logger:
        """
        Build the root logger utility
        :param level: The logging level we want to use
        :return: logging.Logger
        """
        log_location = os.path.join(global_settings['log_location'],
                                    'root.log')
        return self._new_logger('root', log_location, level)

    # -- Protected Interface

    def _new_logger(self, name: str, location: str, level: int) -> logging.Logger:
        """
        Create a new logger that pumps it's output to a rotating
        file handler for when using multiple nodes at once
        :param name: The name of the logger
        :param location: The filpath to 
        :param level: logging.Level to set this item to
        :return: logging.Logger
        """

        if not os.path.isdir(os.path.dirname(location)):
            os.makedirs(os.path.dirname(location))

        formatter = log.BetterFormater(
            fmt=log.MESSAGE_FORMAT.format(''),
            datefmt=log.DATETIME_FORMAT
        )

        handler = logging.handlers.RotatingFileHandler(
            location,
            mode='a',
            maxBytes=global_settings['log_max_bytes_size'],
            backupCount=global_settings['log_backup_count'],
            encoding=None,
            delay=0
        )
        handler.setFormatter(formatter)
        handler.setLevel(level)

        new_log = logging.getLogger(name)
        new_log.addHandler(handler)
        new_log.setLevel(level)

        return new_log


    def _load_settings(self, additional_settings: Optional[dict] = {}) -> None:
        """
        Load our settings config using the ``<hive_location>/config/hive.py``

        .. tip::
            Use the environment variable ``HIVE_SETTINGS`` to provide a path to
            a python file that contains additional settings. This can be useful
            for things like production machines with augmented settings.

        :return: None
        """
        source_file = os.path.join(
            self._hive_root_folder,
            'config',
            'hive.py'
        )
        self.__load_module('hm_settings', source_file)

        if os.environ.get('HIVE_SETTINGS'):
            overloaded_settings = os.environ['HIVE_SETTINGS']
            self.__load_module('hm_override_settings', overloaded_settings)

        global_settings.update(additional_settings)


    def _obtain_root_class(self) -> None:
        """
        Based on the current configuration, load the class that
        defined our RootController.
        :return: subclass of RootController
        """
        source_file, class_name = global_settings['hive_controller']
        self._root_module = self.__load_module(
            'hm_root_controller', source_file
        )
        self._root_class = getattr(self._root_module, class_name)

    # -- Private Interface

    def __load_module(self, name: str, source_file: str) -> types.ModuleType:
        """
        Based on the name and source file, dynamicaly load a new module
        :param name: The name of the module
        :param source_file: The absolute path to our source file
        :return: The loaded module
        """
        # Gnarly Python 3.7+ way of loading a source file
        loader = importlib.machinery.SourceFileLoader(
            name, source_file
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        return mod


    def __get_all_nodes(self) -> list:
        """
        Obtain all classes of nodes.
        """
        sys.path.insert(0, global_settings['hive_root'])
        # We rely on the relative imports for this file
        # so we have to go get it ourselves
        import nodes
        # sys.path.pop(0)
        return [n for n in _Node._registry if not n._abstract]


    def __nodes_from_names(self, names: list) -> list:
        """
        Search for nodes by their simple name
        :param names: list[str] of names
        :return: list[_Node subclass]
        """
        # See __get_all_nodes() for more
        hive_root = global_settings['hive_root']
        sys.path.insert(0, hive_root)
        import nodes

        names = [n.lower() for n in names]
        not_found_names = names[:]
        node_classes = {}

        # First, see if we have it in the registry already
        for node_class in _Node._registry:
            low_class_name = node_class.__name__.lower()

            if low_class_name in names:
                node_classes[low_class_name] = node_class
                not_found_names.remove(low_class_name)

        for node_folder in os.listdir(os.path.join(hive_root, 'nodes')):

            if not os.path.isdir(os.path.join(hive_root, 'nodes', node_folder)):
                continue

            if node_folder.lower() in not_found_names:

                # -- We have a match
                node_count = len(_Node._registry)
                node_module = importlib.import_module(f'nodes.{node_folder}.{node_folder}')
                if node_count == len(_Node._registry):
                    raise HiveError(f'No _Node class found in {node_folder}')

                node_classes[node_folder.lower()] = _Node._registry[-1] # Always appended

        if not len(names) == len(node_classes):
            missing_nodes = set()
            for n in names:
                if n not in node_classes:
                    missing_nodes.add(n)

            raise HiveError(f'Cannot find nodes: {", ".join(missing_nodes)}')

        return node_classes.values()


    def __init_nodes(self) -> list:
        """
        Initialize individual nodes
        """
        lvl = logging.DEBUG if self._verbose else logging.WARNING
        for node_class in self._node_classes:

            loop = asyncio.new_event_loop()

            node_instance = node_class(
                node_class.__name__,
                logger=self.node_logger(node_class.__name__, lvl)
            )

            node_thread = threading.Thread(
                target=node_instance.run,
                name=node_class.__name__,
                args=(loop,)
            )

            node_thread.node_instance = node_instance
            node_thread.daemon = True
            node_thread.start()
            self._node_threads.append(node_thread)


    def __init_root(self) -> None:
        """
        Initialize the root object.

        "Get a fire going!"
            - UGLÚK, Lord of the Rings - The Two Towers

        :return: None
        """
        lvl = logging.DEBUG if self._verbose else logging.WARNING
        self._root_loop = asyncio.new_event_loop()
        self._root_abort = asyncio.Condition(loop=self._root_loop)

        # -- Parameters to pass to our root for easy setup
        self._root_kwargs['logger'] = self.root_logger(lvl)
        self._root_kwargs['startup_condition'] = self._condition
        self._root_kwargs['abort_condition'] = self._root_abort

        self._root_instance = self._root_class(**self._root_kwargs)

        self._root_thread = TerminalThread(
            target=self._root_instance.run,
            name='root_process',
            args=(self._root_loop,),
        )
        self._root_thread.daemon = True
        self._root_thread.start()
        with self._condition:
            # Let's make sure it's runnin before we start making moves
            # with our nodes
            self._condition.wait(60.0)


    def __kill(self) -> None:
        """
        Terminate all nodes and then the root process.

        "May death find your quickly..."
            - Faramir, Lord of the Rings - The Return of the King

        :return: None
        """
        # -- Node destruction
        for node_thread in self._node_threads:
            try:
                node_thread.node_instance.shutdown()
            except Exception as e:
                print (":FAILED TO SHUTDOWN NODE:")
                continue

        # -- Root Destruction
        if self._root_loop and (not self._root_loop.is_closed()):
            future = asyncio.run_coroutine_threadsafe(
                self.fire_abort_root(), self._root_loop
            )
            # Wait for the result:
            result = future.result()


    async def fire_abort_root(self) -> None:
        """
        Execute the condition to abort our root
        :return: None
        """
        async with self._root_abort:
            self._root_abort.notify_all()
