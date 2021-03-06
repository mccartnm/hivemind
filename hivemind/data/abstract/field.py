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

import copy
from enum import Enum, unique, auto

from hivemind.data.query import QueryOperators, QueryFilter

class _AutoName(Enum):
     def _generate_next_value_(name, start, count, last_values):
         return name

@unique
class FieldTypes(_AutoName):

    # -- Numeric
    TINYINT = auto()
    SMALLINT = auto()
    INT = auto()
    BIGINT = auto()
    DECIMAL = auto()
    FLOAT = auto()
    REAL = auto()

    # -- Datetime
    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    # TIMESTAMP = auto()
    # YEAR = auto()

    # -- Characters
    VARCHAR = auto()
    TEXT = auto()

    # -- Blob
    BINARY = auto()

    # -- Secret Sauce Fields
    JSON = auto()

    # -- Relation
    FK = auto()
    # MtM = auto() # yowza

    # -- INVALID
    INVALID = auto()


class FieldMeta(type):
    """
    Metaclass that does field verification for us
    when the interpreter locates new field classes
    """
    _validate = True

    def __init__(cls, name, bases, dct) -> None:
        if not hasattr(cls, '_field_base'):
            cls._field_base = True
            return

        if FieldMeta._validate and cls.base_type == FieldTypes.INVALID:
            raise TypeError(f"Class {cls} requires valid base_type!")

        setattr(bases[0], name, cls)


class _Field(object, metaclass=FieldMeta):
    """
    Abstract representation of a field type
    """

    # Overload per concrete field type
    base_type = FieldTypes.INVALID

    def __init__(self, *args, **kwargs):
        self._pk = kwargs.get('pk', False)
        self._unique = kwargs.get('unique', False)
        self._default = kwargs.get('default', None)
        self._null = kwargs.get('null', False)
        self._db_column = kwargs.get('db_column', None)

        self._table = None # Set by the table metaclass


    def __getattr__(self, key):
        """
        Here's another spot where python some some mad-hattery.

        We use the field to define query filters and this is
        one way to route throug the defaults
        """
        if key in QueryOperators.basic_operators and self._table:
            return QueryFilter.factory(self._table, self, key)
        raise AttributeError(f'_Field instance has no attribute {key}')


    def default_for_sql(self):
        if isinstance(self._default, str):
            return f"'{self._default}'"
        return self._default


    def db_layout(self) -> dict:
        """
        Introspection layout
        """
        return {
            'base_type': self.base_type.name,
            'pk': self.pk,
            'unique': self._unique,
            'has_default': self.has_default,
            'null': self._null
        }


    def db_name(self) -> str:
        if self._db_column:
            return self._db_column

        if self._table:
            return self._table.db_column_name(self.field_name)
        return self.field_name


    @property
    def has_default(self):
        return self._default is not None


    def generate_default(self):
        if callable(self._default):
            return self._default()
        return self._default


    def prep_for_db(self, value):
        return value


    @property
    def pk(self):
        return self._pk


    @classmethod
    def db_type(cls, database) -> str:
        """
        Based on the type, get the proper type from our database
        """
        return database.type_from_base(cls.base_type)
