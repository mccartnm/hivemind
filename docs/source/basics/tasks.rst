*****
Tasks
*****

One of the main reasons ``hivemind`` was invented was to cut down on the overhead of handling various processes communicating with one another. Development can be daunting in these situations. Starting dozens of terminals, making sure the communication was in good enough sync, bashing your head against the wall. It's not the most pleasant experience.

Out of this stemmed an idea. What if we could handle more than just back and forth communication on the hive? What about, say, arbitrary work on the network? Enter ``Tasks``.

The Task System
===============

The task system allows you to set up manually executable operations as well as build cron-like jobs that can execute periodically.

Enough talk! Let's get coding! For now let's start with a new hive.

.. tip::

    We're using the hivemind envrionment described in the install section of these docs!

.. code-block:: shell

    (hm) ~$> mkdir runners
    (hm) ~$> cd runners
    (hm) ~$> hm new runners
    New hive at: /home/jdoe/code/runners

Enabling Tasks
--------------

The task system is known as a ``Feature`` in ``hivemind``. A Feature is a plugin system desgined to add functionality to the core of your hive. This makes it easy to extend the basic library when required and reduce any bloatware when not needed in the network.

To enable the tasks feature, you need to add the proper import path to your hive's ``global_settings['hive_features']`` list.

Within the ``config/hive.py`` file in your new hive, you should see ``HIVE_FEATURES``. Set it to the following:

.. code-block:: python

    HIVE_FEATURES = [
        'hivemind.features.task'
    ]

.. note::

    The default installation may have this line just commented out, simply uncomment it and you're ready to go!

Creating a Task Node
--------------------

A ``TaskNode`` is a ``_Node`` object that, with the feature enabled, hooks up additional utilities with our controll layer. We'll get into more on this in the ``Feature`` documentation but for now, we can initialize a ``TaskNode`` like so:

.. code-block:: shell

    (hm) ~$> hm create_node MyTasks -c hivemind.features.task.TaskNode

.. tip::

    Remember to run the ``hm create_node`` command in the root of your hive!

Once done, you should see the ``mytasks/mytasks.py`` file with the proper imports and class for the new ``TaskNode``.

Creating a TaskYaml
-------------------

This new ``TaskNode`` has all the same functionality as our original ``_Node``\s with services and subscriptions but comes with a significant upgrade.

What is a TaskYaml
++++++++++++++++++

Using the YAML format, we define a series of tasks to execute and properties to work with.

Coming soon...
