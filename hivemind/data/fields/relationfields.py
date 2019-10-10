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
Relationship fields
"""

from hivemind.data.abstract.field import _Field, FieldTypes

class ForeignKeyField(_Field):
    """
    A relationship between two tables.
    """
    base_type = FieldTypes.FK

    CASCADE = 'CASCADE'
    SET_NULL = 'SET NULL'

    def __init__(self, related_class, *args, **kwargs):
        _Field.__init__(self, *args, **kwargs)
        self._related_class = related_class

        self._del_policy = kwargs.get(
            'del_policy', ForeignKeyField.CASCADE
        )

        if not self._null and self._del_policy == self.SET_NULL:
            raise TypeError(
                'Cannot have a not-null field use SET_NULL'
            )


    @property
    def deletion_policy(self):
        return self._del_policy


    @property
    def related_class(self):
        return self._related_class
    

    def prep_for_db(self, value):
        """
        If we're searching with an instance of an object, we return
        the primary key.
        :param value: value to augment
        :return: key of table instance or the original value
        """
        from hivemind.data.abstract.table import _TableLayout
        if isinstance(value, _TableLayout):
            return value.pk_value
        return value
