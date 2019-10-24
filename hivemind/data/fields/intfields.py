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
Basic fields surrounding the int type
"""
import functools
import itertools
from datetime import datetime, timezone, timedelta

from hivemind.data.abstract.field import _Field, FieldTypes

HIVEMIND_EPOCH = datetime(2019, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
BASIC_TICK = itertools.count()
SHARD_ID = 1

class IntField(_Field):
    """
    Basic integer field
    """
    base_type = FieldTypes.INT


class TinyIntField(_Field):
    """
    Basic integer field
    """
    base_type = FieldTypes.TINYINT


class SmallIntField(_Field):
    """
    Basic integer field
    """
    base_type = FieldTypes.SMALLINT


class BigIntField(_Field):
    """
    Basic integer field
    """
    base_type = FieldTypes.BIGINT


class IdField(_Field):
    """
    Field that uses some magic to generate itself!
    """
    base_type = FieldTypes.BIGINT

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', IdField._build_id) 
        super().__init__(*args, **kwargs)


    @staticmethod
    def date_to_int(datetime):
        """
        :param datetime: Timezone aware datetime that we're converting to an int
        :return: int
        """
        diff = datetime - HIVEMIND_EPOCH
        delta = (diff.days * 86400000) + (diff.seconds * 1000) + (diff.microseconds / 1000)
        return int(delta)


    @staticmethod
    def _build_id():
        """
        Python menthod of constructing an id a-la instagrams setup
        https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c
        """
        # 1: Timestamp
        current_id = IdField.date_to_int(datetime.utcnow().replace(tzinfo=timezone.utc)) << 23

        # 2: Shard ID (For now, always one)
        current_id |= SHARD_ID << 10

        # 3: Auto-incr with the last 10 bits
        current_id |= next(BASIC_TICK) % 1024

        return current_id


    @staticmethod
    def to_datetime(timestamp):
        """
        :return: datetimte.datetime
        """
        return HIVEMIND_EPOCH + timedelta(microseconds=(timestamp >> 23) * 1000)
