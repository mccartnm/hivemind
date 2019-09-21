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

Simple straight string expressions
"""

from purepy import override

from .expr import _VariableExpansionExpression, ExprVariable

class LowercaseExpr(_VariableExpansionExpression):
    """
    Lowercase a string
    """
    name = 'low'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        return value.lower()


class UppercaseExpr(_VariableExpansionExpression):
    """
    Lowercase a string
    """
    name = 'up'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        return value.upper()


class CapitalizeExpr(_VariableExpansionExpression):
    """
    Lowercase a string
    """
    name = 'cap'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        return " ".join(w.capitalize() for w in value.split())


class QuoteExptr(_VariableExpansionExpression):
    """
    Quote a given string with the provided char(s)
    quoute(<char>='"')
    """
    name = 'quote'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        char = '"'
        if args:
            char = args[0]
        return f'{char}{value}{char}'


class TrimExpr(_VariableExpansionExpression):
    """
    Trime the string of leading and trailing whitespace
    """
    name = 'trim'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        return value.strip()


class TruncateExpr(_VariableExpansionExpression):
    """
    Truncate a string based on the arguments supplied.
    trunc(<count>, <from_start>=False)
    """
    name = 'trunc'

    @override()
    def evalute(self, value: ExprVariable, *args) -> str:
        if not args:
            return value
        
        try:
            count = int(args[0])
        except ValueError as err:
            # Some kind of loggin?
            return value

        if len(args) > 1 and args[1] not in ('False'):
            return value[count:]
        return value[:count]
