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

Simple expressions that can be run on iterables
"""
from purepy import override

from .expr import _VariableExpansionExpression, ExprVariable


class JoinExpr(_VariableExpansionExpression):
    """
    Join a list of values into a common string join(<sep>)
    """
    name = 'join'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        if not args:
            return ''.join(value)
        return args[0].join(map(str, value))


class CountExpr(_VariableExpansionExpression):
    """
    Given an iterable, return the number of items.
    """
    name = 'count'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        return str(len(value))