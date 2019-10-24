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

from .field import _Field, FieldTypes
from typing import Any

# -- This will import any basic fields
from hivemind.data import fields
from hivemind.util import misc

class _TableMeta(type):
    """
    Metaclass for the _TableLayout that helps reserve fields on the class
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
                value.field_name = attr
                value._table = cls

        if not primary_key_field:
            # We'll always want some form of primary key
            setattr(cls, 'id', _Field.IdField(pk=True))
            cls._internal_field_order.insert(0, 'id')
            cls._internal_fields['id'] = cls.id
            cls.id.field_name = 'id'
            cls.id._table = cls


class _TableLayout(object, metaclass=_TableMeta):
    """
    Object representation of a table in the database
    """
    class DoesNotExist(Exception):
        pass

    def __init__(self, database, **kwargs):
        """
        Initialize an instance of the model based on the values passed in
        """
        self._database = database

        for name, field in self._internal_fields.items():
            setattr(self, name, kwargs.get(name, None))


    def __eq__(self, other):
        return self.pk_value == other.pk_value


    def __getattribute__(self, key):
        """
        Before you say anything, this is intensional. We have to be extra
        crafty when pulling down relationships
        """
        if key == '_internal_fields' or key not in self._internal_fields:
            return super().__getattribute__(key)

        if self._internal_fields[key].base_type == FieldTypes.FK:

            # Go get the thing
            value = super().__getattribute__(key)
            if isinstance(value, _TableLayout) or value is None:
                return value
            else:
                field = self._internal_fields[key]
                value = self._database.new_query(
                    field.related_class,
                    **{field.related_class.pk(): value}
                ).get()
                setattr(self, key, value)
                return value

        return super().__getattribute__(key)


    @classmethod
    def db_layout(cls) -> dict:
        """
        Obtain the layout of this table and it's fields for
        intropection
        """
        return {
            'name' : cls.db_name(),
            'fields' : [[n, cls._internal_fields[n].db_layout()] for n in cls._internal_field_order]
        }


    @classmethod
    def db_name(cls) -> str:
        if hasattr(cls, 'db_table'):
            return cls.db_table
        return misc.to_camel_case(cls.__name__)


    @classmethod
    def db_column_name(cls, field: (str, _Field)) -> str:
        """
        :param python_name: The name of the attribute
        :return: The database-friendly name of the column
        """
        if isinstance(field, str):
            field_name = field
        elif isinstance(field, _Field):
            field_name = field.db_name()
        else:
            raise TypeError(
                f'Cannot convert {type(field)} to column name'
            )

        return misc.to_camel_case(field_name)


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
    def pk(cls) -> str:
        f = cls.pk_field()
        if f:
            return cls.db_column_name(f.field_name)
        return None


    @classmethod
    def pk_field(cls) -> _Field:
        for name, field in cls._internal_fields.items():
            if field.pk:
                return field
        return None


    @property
    def pk_value(self) -> Any:
        """
        :return: The value of the primary key, whatever it might be
        """
        field = self.pk_field()
        return getattr(self, field.field_name)


    @classmethod
    def get_field(cls, field_name: str) -> _Field:
        try:
            return cls._internal_fields[field_name]
        except KeyError as e:
            raise KeyError(
                f'The field: {field_name} does not exist on {cls.__name__}'
            )


    @classmethod
    def _create_from_values(cls, database, values):
        """
        Temporary crutch to build an item from values coming from
        the database
        """
        new_instance = cls(database)

        for i, name in enumerate(cls._internal_field_order):
            field = cls._internal_fields[name]

            if isinstance(field, _Field.IdField) and field.pk:
                # Make a created_on field
                setattr(new_instance,
                        'created_on',
                        _Field.IdField.to_datetime(values[i]))

            setattr(new_instance, name, values[i])

            if field.base_type == FieldTypes.FK:
                setattr(new_instance, f'{name}_pk', values[i])

        return new_instance


    @classmethod
    def unqiue_constraints(cls) -> tuple:
        """
        Return any unique constraints for fields by overloading
        this.
        :return: tuple(tuple(str),)
        """
        return tuple()
