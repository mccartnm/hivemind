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

Abstract command utilities
"""

from argparse import ArgumentParser, REMAINDER, Namespace

from typing import TypeVar, Generic
from ..misc import SimpleRegistry, run_process

T = TypeVar('TaskYaml')


class CommandError(RuntimeError):
    """ Exception pertaining to the command tools """
    pass


class _AbstractCommand(object, metaclass=SimpleRegistry):
    """
    Command base for the arsenal of platform agnositc commands
    that hivemind.util comes with as well as a simple way for
    developers to add their own.

    To create a command, you overload this and define the three
    functions

    .. code-block:: python
        
        def description(self) -> str: ...
        def populate_parser(self, parser: ArgumentParser) -> None: ...
        def exec_(self, task_data: T) -> None: ...

    The registry for this class is built as your subclass is
    imported so there's no additional registration required.

    .. todo::

        Need an environment variable that will load these
        additional clases on startup of hivemind. Or possibly
        some other such methods for the concept of a Hivemind
        Project
    """
    name = None

    #
    # A known return value that means we're jumping out of
    # a function
    #
    RETURN_ = 'RETURN_'

    def __init__(self, *arguments: str) -> None:
        self._data = None
        self._arguments = arguments
        self._parser = ArgumentParser(
            prog=(self.name or 'command'),
            description=self.description()
        )
        self.populate_parser(self._parser)


    def __repr__(self) -> str:
        detail = self.name or 'Generic'
        return f'<Command({detail})>'


    def __str__(self) -> str:
        detail = self.name or 'Generic'
        return f'{detail}({self._arguments})'


    @property
    def data(self) -> Namespace:
        """
        :return: argparge.Namespace instance that we've built
                 from our arguments
        """
        assert self._data is not None,
               "Arguments have not been parsed!"
        return self._data


    @classmethod
    def command(cls, name: str) -> _AbstractCommand:
        """
        Based on the name, find the given class. Raise an exception
        if it cannot be found.

        :param name: The name of our command
        :return: subclass of _AbstractCommand
        """
        if not name.lower() in cls._registry:
            raise CommandError(f'HM Command not found {name}')
        return cls._registry[name.lower()]
    

    # -- Virtual Interface

    def description(self) -> str:
        """
        Overload this to preset the user we a pretty description
        of the command.

        :return: str
        """
        return 'Command line execution'


    def populate_parser(self, parser: ArgumentParser) -> None:
        """

        Overload this to populate an argparse.ArgumentParser
        for customized commands.

        :param parser: ``argparse.ArgumentParser`` instance
        :return: None
        """
        parser.add_argument(
            'args', nargs=REMAINDER,
            help='arguments for our subprocess'
        )


    def exec_(self, task_data: T) -> None:
        """
        Execute the command itself. By default this just runs the
        arguments in a subprocess. Custom commands will augment this
        proceedure.

        :param task_data: TaskYaml instance that we can use in the
                          command.
        :return: None
        """
        result = run_process(self._arguments)
        if result != 0:
            raise CommandError(
                f"Failed command: {' '.join(self._arguments)}"
            )

    # -- Proctected methods

    def _process_args(self) -> None:
        """
        To go from raw arguments -> processed parameters we throw
        it into our parser. We don't do this right away because we
        may just be using the parser to auto generate documentation

        :return: None
        """
        self._data = self._parser.parse_args(self._arguments)
