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
from hivemind.core.base import _HivemindAbstractObject


# -- Constants
kRequest = 'request'
kCron = 'cron'

kTaskTypes = [
    kRequest, #< A job set up with our controllers that can be activated
    kCron     #< A cron utility that runs at a given time
]

class _Task(_HivemindAbstractObject):
    """
    A specific work unit that we can set up as a cron job or
    call upon from the root network.
    """
    def __init__(self, node, name, descriptor, config):
        self._node = node
        self._name = name
        self._descriptor = descriptor
        self._config = config


    @property
    def node(self):
        return self._node


    @property
    def name(self):
        return self._name


    @property
    def type(self):
        return self._descriptor['type']


    @property
    def endpoint(self):
        return f'/task/{self.node.name}/{self.name}'


    def function(self, *args):
        print (f"_FUNCTION_FOR_{self.name}")

    # __START_HERE__
    #
    # Idea for cron:
    # Have the cron run and then calculate the difference
    # in time to the next execution then just bring up
    # a wait condition that will pause until then. In the
    # event of a shutdown, simply check for an abort!
    # Simple.
    #
