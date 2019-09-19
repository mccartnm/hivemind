
from purepy import override

import sqlite3

class SQLiteInterface(_DatabaseScafolding):
    """
    sqlite interface. A Basic, but quick and easy interface.
    """

    name = 'sqlite'

    def __init__(self):
        _DatabaseScafolding.__init__(self)
        self.__db = None


    @override()
    def connect(self, database_name, **kwargs):
        """
        Connect to a single local file
        """
        if not database_name.endswith('.db'):
            database_name += '.db'
        self.__db = sqlite3.connect(database_name)


    @override()
    def execute(self, query, values):
        """
        Raw, low level query interface
        """

