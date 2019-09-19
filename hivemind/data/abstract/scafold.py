"""
Abstract interface with a database api
"""

from purepy import PureVirtualMeta, pure_virtual

from hivemind.data.db import _TransactionManager

class _DatabaseScafolding(metaclass=PureVirtualMeta):
    """
    Overload per database api
    """
    name = None


    def __init__(self):
        self.__tm = _TransactionManager(self)

        self._connect()

    # -- Virtual Interface

    @pure_virtual
    def connect(self, database_name, **kwargs):
        """
        Connect to a given database
        """
        raise NotImplementedError()


    @pure_virtual
    def execute(self, query, values):
        """
        Execute a query
        """
        raise NotImplementedError()


    # -- Public Interface


    # -- Private Interface

    def _init_database(self):
        """
        
        """

        self._create_table("hm_migrations", MigrationTable)
        self._create_table("hm_data_store", DataStoreTable)


    def _connect(self):
        
