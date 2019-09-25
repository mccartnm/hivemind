***********
Quick Start
***********

``hm`` Command
==============

When building a hivemind project, colloquially known as a "hive", the CLI interface comes with utilities to help initialize the project, new nodes, and even run in development and production environments.

.. execute_code::
    :hide_code:
    :hide_headers:

    from hivemind.util.cliparse import build_hivemind_parser
    parser = build_hivemind_parser()
    parser.print_help()


Create a Project
================

Let's go to wherever we normally keep our code repos and make a new directory, we'll call it ``intercept``.

.. code-block:: shell

    ~$> cd ~/repos
    ~$> mkdir intercept
    ~$> cd intercept

Once inside, we use the ``hm new`` command to set up a fresh hive.

.. code-block:: shell

    ~$> hm new intercept
    New hive at: /home/jdoe/repos/intercept

If you look around there, you'll see something akin to the following structure.

.. code-block:: text

    intercept/
        `- intercept/
            `- config/
                `- __init__.py
                `- hive.py
            `- nodes/
                `- __init__.py
            `- root/
                `- __init__.py
            `- static/
            `- templates/
            `- __init__.py

.. tip::

    While not specifically required, the additional top level directory is to contain all the python parts to one location to avoid crowding the root or your new repo.

There's a lot of files there and we'll get into them soon but for now, let's bring the hive online. With just that one command, we have a functional webserver that can be navigated to.

.. code-block:: shell

    ~$> cd intercept
    ~$> hm dev

The ``dev`` command should boot up your hive and start listening.

.. tip::

    While this will be described better in the logging documentation, you should be able to find the log of your hive wherever you're ``config/hive.py -> LOG_LOCATION`` is set.

Now, simply navigate to ``http://127.0.0.1:9476`` and you should be greeted with a simple (but noteworthy!) page.

A Quick Recap
-------------

- The ``hm new`` command created a "blank" hive with some defaults.
- The ``hm dev`` command starts the hive environment
- A basic webserver is run and we were able to see the page!

.. note::

    The webserver you're seeing is actually your hive's ``RootController`` listening and responding to changes in your network. We'll describe this in greater detail later. This is a vital piece of the puzzle so remember the name!


Create a Node
=============

Ok, so we have the infrastructure. Time to put some nodes on it!
