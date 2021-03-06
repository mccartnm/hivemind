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
from typing import TypeVar, Generic, Union
from purepy import pure_virtual

from ..misc import PV_SimpleRegistry

T = TypeVar('TaskYaml')
ExprVariable = Union[str, list]

class ExpressionError(Exception):
    pass

class _VariableExpansionExpression(object, metaclass=PV_SimpleRegistry):
    """
    Quick registry/abstract class for generic string expressions when handling
    the vairable expansion and other utilities.

    .. todo::

        proper docs
    """
    name = None

    def __init__(self, task_data: T) -> None:
        self._task_data = task_data


    @classmethod
    def _get_expressions_layout(cls) -> str:
        output = ''
        for name, cls_ in cls._simple_registry.items():
            output += ' - ' + name + ': \n'
            output += (' ' * 4) + cls_.__doc__.strip()
            output += '\n'
        return output[:-1] # Remove the last new line


    @property
    def task_data(self) -> T:
        """
        :return: ``common.abstract._AbstractFLaunchData``
        """
        return self._task_data    


    @pure_virtual
    def evalute(self, value: ExprVariable, *args) -> str:
        """
        A pure virtual function that must be overloaded to handle
        the expression
        """
        raise NotImplementedError("Overload run()") # pragma: no cover


    @classmethod
    def compute(cls, name: str, value: ExprVariable, task_data: T) -> str:
        """
        Evaluate the expression.

        :param name: The name of the command, this can potentially contain arguments
        :param value: The value that we're going run the expression on
        :param task_data: TaskYaml instance with our proerties and such
        :return: str computed value
        """
        args = []
        search = name.strip()

        if '(' in name:
            search = name[:name.index('(')]

            # For the time being, we're assuming that the 
            args_unparsed = name[name.index('(') + 1 : -1]

            current_arg = ''
            last_index = len(args_unparsed) - 1

            quote = False
            qchar = ''
            echar = False

            #
            # Do a micro parse on the arguments within our expression
            # FIXME: This could be way better
            #
            for i, char in enumerate(args_unparsed):
                if char == '\\':
                    echar = True
                    continue

                if not echar:
                    if char in ('"', "'"):
                        if char == qchar:
                            quote = False
                            qchar = ''
                        else:
                            quote = True
                            qchar = char

                        # If we're here, make sure we catch the last index
                        if i == last_index and current_arg:
                            args.append(current_arg)
                        continue

                else:
                    echar = False

                if char == ',' and current_arg and not quote:
                    args.append(current_arg)
                    continue

                if char == ' ' and current_arg == '' and not quote:
                    continue

                current_arg += char

                if i == last_index and current_arg:
                    args.append(current_arg)

        if not search in cls._simple_registry:
            raise ExpressionError(f'The expression: "{search}" cannot be found!')
        return cls._simple_registry[search](task_data).evalute(value, *args)
