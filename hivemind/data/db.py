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
from collections import deque

class TransactionManager(object):
    """
    Context manager for handling transactions in the database

    .. code-block:: python

        class MyHive(RootController):
            # ...

            def do_some_transaction(self):
                with self.database.transaction:
                    self.perform_sql()

    """

    def __init__(self, integration):
        self._integration = integration

        self._transaction_stack = deque()
        self._cursor = None


    @property
    def active(self):
        return self._cursor


    def __enter__(self):
        """
        Start a transaction. This may vary depending on the
        use case
        """
        self._transaction_stack.append(1)
        if not self._cursor:
            self._cursor = self._integration.get_db_cursor()

        begin_sql = self._integration.begin_sql()
        self._integration.execute(begin_sql)


    def __exit__(self, type, value, traceback):
        """
        When we exit this transaction magic, we need to
        commit any changes, unless of course there's an
        error at which point we need to rollback completely
        """
        self._transaction_stack.pop()

        if traceback:
            rollback_sql = self._integration.rollback_sql()
            self._integration.execute(rollback_sql)
        else:
            commit_sql = self._integration.commit_sql()
            self._integration.execute(commit_sql)

        if len(self._transaction_stack) == 0:
            self._cursor = None # No longer need the cursor
