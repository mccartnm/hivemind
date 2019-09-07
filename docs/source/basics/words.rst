*********
Interface
*********

:=TODO=:

Resilience
==========

In almost all movies, the big bad hive mind villain is taken down by the heroes simply killing of the "brain." This is because, ultimately, that design is flawed (duh). Instead of one omnipotent centralized control, ``hivemind`` attempts to avoid that catastrophic end by simply duplicating the brain and keeping a running interface between each of them. Unless *all* the brains are dead, the system lives on.


Nomenclature
============

There are a few buzz words that are used constantly throughout hivemind so here's a quick cheat sheet to get you started.

.. glossary::

    Controller
        Responsible for managing nodes and data

    Node
        A single entity that carries out a given value of work *or* listens for subscribed data to process

    Service
        A single unit of work. This can send payloads of data to our Controller for proper routing

    Subscription
        A single endpoint listening for payloads sent by services. This allows us to separate data gathering with data processing
