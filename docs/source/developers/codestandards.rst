**************
Code Standards
**************

Hivemind uses the "PEP8-ish" mentality. The original author of Hivemind was never a huge fan of some of the items in that document but, for the most part, it's a good thing to strive for.

Classes
-------

For "abstract" classes, we prefix with ``_``

.. code-block:: python

    class _MyAbstract(...):
        # ...

For concrete or "final" classes, we use PEP8

.. code-block:: python

    class MyConcrete(_MyAbstract):
        # ...

Class Methods
-------------

When writing up functions within a class, to PEP8s dismay, we prefer to use two new lines rather than just one between them. A little space in the code tends to ease the stress of digesting it all.

Annotations, while not required, are encouraged where they make sense.

.. code-block:: python

    class Foo(object):
        """
        Some Doc String
        """

        def __init__(self, x: int):
            self._x = x
            self._y = 1


        def get_x(self) -> int:
            """
            Get the x value

            :return: The value of x
            :rtype: int
            """
            return self._x


        @property
        def y(self) -> int:
            """
            Obtain the current value of y

            :rtype: int
            """
            return self._y


        @y.setter
        def set_y(self, new_value: int):
            """
            Setter for the value of y

            :param new_value: 
            """
            assert self._y < new_value, "Cannot move y down!"
            self._y = new_value
