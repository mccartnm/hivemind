**********
Primitives
**********

Layers
======

There are three layers within ``hivemind``.

.. code-block:: none

                 + --------------------------------------------- +
    Data Layer > |           [ Data Layer ] <-- Eventually       | Backend
                 |                 |                             |
                 +-----------------|-----------------------------+
    Control    > |         [    Controller   ]                   | Network
                 |           |       |      |                    |
    Node       > |       [ Node ] [ Node ] [ Node ]              |
                 +-----------------------------------------------+

1. The Data Layer
2. The Control Layer
3. The Node Layer

The Data Layer
--------------

This will be a layer added in after initial functionality has been written up. It will consist of a database that contains a select control groups' identity and registration utilities. (There's a lot more planned but leaving this for now)

The Control Layer
-----------------
The control layer consists of a "manager" (eventually multiple managers) that can oversee registered nodes, their subscriptions and services, as well as dispatch messages based on the required data.

As the ``Data Layer`` becomes available, some of the duties will move to that but ultimately the controller is where the brain lives.

The Node Layer
--------------

A Node is a single entity that can host any number of services and add handlers for any number of subscriptions. In optimal design, a node only ever hosts a single service but there is obviously no restriction. Each service lives on a unique thread that will do any processing required.

As you add nodes to your network the root controller(s) handle the dispatching of required information for you.


Backend
=======

This just refers to the ``Data Layer`` but more specifically both the database and protocol working back and forth from it to the controllers.

Network
=======

This is the grouping of all node-like objects including both controllers and working nodes. All communication, currently, uses basic TCP to work between each process.


Resilience
==========

In almost all movies, the big bad hive mind villain is taken down by the heroes simply killing of the "brain." This is because, ultimately, that design is flawed (duh). Instead of one omnipotent centralized control, ``hivemind`` attempts to avoid that catastrophic end by simply duplicating the brain and keeping a running interface between each of them. Unless *all* the brains are dead, the system lives on.