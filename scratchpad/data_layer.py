
"""
The Data Layer (Brainstorm)
--------------

The data layer is built to act as a repository of generalized
information that both the controller and any nodes can access
it as required.

+---------------------------+
|         Database          |
+-----\/------------\/------+ <- DB Interface Layer
|   Control       Control   |
+---\/---\/-------\/---\/---+
|   Node Node     Node Node |
+---------------------------+

Database, in this case, can be any number of configurations.
Which leads us to the DB Interface Layer (dBIL).

The abstract _DatabaseScafolding is subclassed in a plugin
style effort to host any database software. An example would
be PostgreSQLIntegration or SQLiteIntegration. These expose a
set of bare-bones api's that allow us to work with tables and
content on the data layer.

Surrounding the database interaction is a _TransactionManager
to handle any BEGIN/COMMIT commands. This should be well
integrated into the database integrations for something like:
"""

from hivemind.data.db import connection

def do_something():

    conn = connection()

    # A single transaction
    with conn.transaction():
        conn.add_data(foo="bar", baz="yellow", blitz="schmoo")
        conn.remove_data("foo", "baz")

        # raise TypeError() # Would rollback the changes

    data = conn.get("blitz")

"""
This leads us to a possibly more important topic, how are we
mapping our data to the dBIL? ORMs tend to be complex and slow
but powerful for fast and effective OOP.

Some kind of hybrid approach might be best.

Option:

    Use the Node and it's registration protocol to actually
    build a data cluster centered around the names of the
    services and possibly some form of configuration.
"""

class PersonData(_Table):
    """
    ORM-style class that the node can use to build/mogrify
    a table on the data layer

    Some kind of method structure that let's use build a set of
    migrations if need be (e.g. we want to add/remove a field or
    rename one based on existing table data)
    """
    def version_1(self):
        self.add_field("id", _Field.integer(auto=True, pk=True))
        self.add_field("first_name", _Field.string())
        self.add_field("last_name", _Field.string())
        self.add_field("email", _Field.string(unique=True))
        self.add_field("location", _Field.string())

    def version_2(self):
        self.remove_field("email")
        self.rename_field("location", "address")


"""
When we pass this information to the controller cluster, it knows
to manipulate the tables as needed and update the schema table(s)
for future startups of the node's tables.
"""


class PersonNode(_Node):

    def services(self):
        self._person_service = self.add_service(
            'person-service',
            self._person_cb,
            execute_count=1
        )


    def data_tables(self):
        #
        # Alert the root cluster to our table and
        # hold a reference to it.
        #
        self._person_data = self.add_data_table(
            PersonData
        )


    def _person_cb(self):
        """
        
        """
        self._person_service.


# TODO... There are still a lot of moving pieces to figure out for this and I'm not in love with it all...