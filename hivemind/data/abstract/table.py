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

from .field import _Field

# -- This will import any basic fields
from hivemind.data import fields

class _TableMeta(type):
    """
    Metaclass for the _TableLoyout that helps reserve fields on the class
    and convert them to the right type of item
    """
    def __init__(cls, name, bases, dct) -> None:
        if not hasattr(cls, '_base'):
            cls._base = True # We ignore the base
            return

        cls._internal_field_order = []
        cls._internal_fields = {}

        primary_key_field = None

        for attr, value in dct.items():
            if isinstance(value, _Field):

                if value.__class__ == _Field:
                    raise TypeError(
                        f'Field: "{value}" is not a valid subclass of _Field!'
                    )

                if value.pk:
                    if primary_key_field:
                        raise TypeError(
                            f'Table: "{name}" too many primary keys!'
                        )
                    primary_key_field = value

                cls._internal_field_order.append(attr)
                cls._internal_fields[attr] = value

        if not primary_key_field:
            # We'll always want some form of primary key
            setattr(cls, 'id', _Field.IdField(pk=True))
            cls._internal_field_order.insert(0, 'id')
            cls._internal_fields['id'] = cls.id


class _TableLayout(object, metaclass=_TableMeta):
    """
    Object representation of a table in the database
    """

    @classmethod
    def db_name(cls) -> str:
        if hasattr(cls, 'db_table'):
            return cls.db_table
        return cls.__name__.lower().replace(' ', '_')


    @classmethod
    def db_column_name(cls, python_name: str) -> str:
        """
        :param python_name: The name of the attribute
        :return: The database-friendly name of the column
        """
        return python_name


    @classmethod
    def columns(cls) -> list:
        """
        :return: list[str, _Field]
        """
        output = []
        for name in cls._internal_field_order:
            output.append([name, cls._internal_fields[name]])
        return output


    @classmethod
    def pk(cls) -> _Field:
        for name, field in cls._internal_fields.items():
            if field.pk:
                return cls.db_column_name(name)
        return None


    @classmethod
    def get_field(cls, field_name: str) -> _Field:
        return cls._internal_fields[field_name]


    @classmethod
    def _create_from_values(cls, values):
        """
        Temporary crutch to build an item from values coming from
        the database
        """
        new_instance = cls()
        idx = 0

        for name in cls._internal_field_order:
            field = cls._internal_fields[name]
            setattr(new_instance, name, values[idx])
            idx += 1

        return new_instance
