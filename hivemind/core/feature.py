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

from hivemind.util.misc import SimpleRegistry

class _Feature(object, metaclass=SimpleRegistry):
    """
    A feature is essentially a plugin that defines additional
    tables, endpoints, and functionality, for our hive core.

    A _Feature can overload a various set of functions
    """

    def __init__(self, controller) -> None:
        self._controller = controller


    @property
    def controller(self):
        return self._controller


    @property
    def lock(self):
        return self.controller.lock


    @property
    def database(self):
        return self.controller.database


    def endpoints(self) -> list:
        """
        Override to provide specfic endpoints to the root
        webserver

        :return: list[tuple(method:str,
                            path:str,
                            callback:callable)]
        """
        return []


    def tables(self) -> list:
        """
        Override to provide tables for our data layer to
        create for later consumption

        :return: list[_TableLayout class,]
        """
        return []
