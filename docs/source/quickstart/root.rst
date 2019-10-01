************
Starting Off
************

What is a Hive
==============

A hivemind project, colloquially known as a "hive", is an organizational structure for all components of the hivemind universe. With a number of benefits over one-off files, the hive provides benefits for development and production environments alike. All while keeping the handcuffs off for when programmers want to do the awesome hackery that Python is known for.

.. tip::

    Think of a city. A bustling of people and information. When walking through the streets, you don't care about what most people or things are doing. You observe and relay information to people who are listening all while potentially listening in on others when the time is right.

If you're familiar with the Django_ project, this should feel very familiar as many of the concepts were modeled after it's project structure.

``hm`` Command
==============

The CLI interface for hivemind. This comes with utilities to help initialize the project, new nodes, and even run in development and production environments. Below is the current help info of the ``hm`` command

.. execute_code::
    :hide_code:
    :hide_headers:

    from hivemind.util.cliparse import build_hivemind_parser
    parser = build_hivemind_parser()
    parser.print_help()


Create a Project
================

Let's go to wherever we normally keep our code repositories and make a new directory. To follow with our "hive as a city" concept, we'll call it ``gotham``.

.. code-block:: shell

    ~$> cd ~/repos
    ~$> mkdir gotham
    ~$> cd gotham

Once inside, we use the ``hm new`` command to set up a fresh hive.

.. execute_code::
    :hide_code:
    :hide_headers:

    from hivemind.util.cliparse import build_hivemind_parser
    parser = build_hivemind_parser()
    parser.subparser_map['new'].print_help()


.. code-block:: shell

    ~$> hm new gotham
    New hive at: /home/jdoe/repos/gotham

If you look around there, you'll see something akin to the following structure.

.. code-block:: text

    gotham/
        `- gotham/
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

- ``config/hive.py``: The settings file for a given hive
- ``nodes/``: Where our nodes will go. More on this soon.
- ``root/__init__.py``: The controller class goes here. The controller(s) is/are the heart of the hive. By default, it's just a transparent wrapper around the ``RootController`` class.
- ``static/``: For web-side utilities, static files that we'll serve out
- ``templates/``: ``TaskYaml`` templates for plugin-style task fun! We'll get more into this later on too.

.. tip::

    While not specifically required, the additional top level directory is to contain all the python parts to one location to avoid crowding the root or your new repo.


With just that one command, we have a functional web server that can be navigated to.

.. code-block:: shell

    ~$> cd gotham
    ~$> hm dev

The ``dev`` command should boot up your hive and start listening.

.. tip::

    While this will be described better in the logging documentation, you should be able to find the output log of your hive wherever you're ``config/hive.py -> LOG_LOCATION`` is set.

Now, simply navigate to ``http://127.0.0.1:9476`` and you should be greeted with a simple (but noteworthy!) page.

A Quick Recap
-------------

- The ``hm new`` command created a "blank" hive with some defaults.
- The ``hm dev`` command starts the hive environment
- A basic web server is run and we were able to see the page!

.. note::

    The web server you're seeing is actually your hive's ``RootController`` listening and responding to changes in your network. We'll describe this in greater detail later. This is a vital piece of the puzzle so remember the name!


Create a Node
=============

Okay, we have a network. Time to put some nodes on it! Enter the ``hm create_node`` command.

.. execute_code::
    :hide_code:
    :hide_headers:

    from hivemind.util.cliparse import build_hivemind_parser
    parser = build_hivemind_parser()
    parser.subparser_map['create_node'].print_help()

.. code-block:: shell

    ~$> hm create_node BatSignal

Once run, you should see the following in your hive.

.. code-block:: text

    nodes/
        `- __init__.py
        `- batsignal
            `- __init__.py
            `- batsignal.py

And ``batsignal.py`` should look something like:

.. code-block:: python

    """
    BatSignal node for gotham
    """
    from hivemind import _Node


    class BatSignal(_Node):
        """
        BatSignal Implementation
        """

        def services(self) -> None:
            """
            Register any default services
            :return: None
            """
            return


        def subscriptions(self) -> None:
            """
            Register any default subscriptions
            :return: None
            """
            return

    if __name__ == '__main__': # pragma: no cover
        # An initialization command.
        BatSignal.exec_(
            name="mynode",
            logging='verbose'
        )

That's a self contained node that can be run but, at the moment, it doesn't do anything.

Enable The Node
---------------

If we run ``hm dev`` right now, nothing will have changed. We need to tell the hive to load the ``BatSignal`` by default.

In the ``nodes/__init__.py`` file you should see the following:

.. code-block:: python

    # from .batsignal import batsignal

Simply uncommenting that grants access to the components powering your hive. This is a pretty brute force way to (dis|en)able nodes.

Add a Service
-------------

.. tip::

    **What is a Service?**

    A service is how we communicate observed data to our network. A service executes on it's own thread and, philosophically, relies on nothing but itself. This doesn't mean it shouldn't interact with other data but, at all costs, we avoid synchronous waiting patterns.

With the node enabled, running ``hm dev`` will start up the controller and our node, but until we add services or subscriptions, our node doesn't serve any purpose. To get the Dark Knight to save us, we'll need to send him a message whenever a crisis occurs. A perfect situation for a service.

.. code-block:: python

    class BatSignal(_Node):
        # ...

        def services(self) -> None:
            """
            Add the bat signal service!
            """
            self._bat_signal_service = self.add_service(
                name='bat-signal-main',
                function=self._bat_signal
            )


        def _bat_signal(self, service) -> int:
            """
            Run the service! By default, this is run on a
            loop forever!
            :param service: The service instance we created above
            :return: int (0 means continue, otherwise abort)
            """

            # Send a signal to the big man himself. (JSON compliant payload)
            service.send('Batman! We need help!')

            # As lowly cityfolk, we can do nothing but wait until
            # the next crisis.
            service.sleep_for(5.0)

            return 0


A few important things in there.

1. We defined our first ``_Service`` with the ``self.add_service`` function.
    - ``name``: A name for our service (unique to the node class)
    - ``function``: The callback that gets run in a loop for the rest of the _Node's life
2. Within the callback function, we sent a message through our service to alert anyone that's listening
3. To avoid spamming the controller and subsequent subscriptions to this service, we have the service sleep
    - We do this with ``service.sleep_for`` as it has the ability to wake up gracefully when shutting down

.. warning::

    Avoid ``time.sleep`` in a service callback! There's no benefit over ``_Serivce.sleep_for`` and can
    cause your program to stall out for a length of time.


Logs
----

With the service looking good, we can start our development environment with ``hm dev``. At the moment, nothing new will appear to happen. Our service should be transmitting a signal every 5 seconds, but we don't have anything to really look at. To see what's happening at a log level, navigate to where your ``config/hive.py -> LOG_LOCATION`` points you. (This will be different on different platforms).

You should see two logs. One called ``root.log`` and another called ``batsignal.log`` (or whatever you called the node class). The logging utilities within hivemind route to the corresponding log file to keep them from all becoming one giant mess. In the future ``hm`` may gain the ability to merge the log based on the timestamps to help improve with time debugging.

.. tip::

    **Verbose** To enable verbose output of the nodes, use the ``-v`` flag. This will be reflected in the logs, not on the standard output

    .. code-block:: shell

        ~$> hm dev -v



Add a Subscription
------------------

The Batman is always vigilant to save the day. A subscription, is no different.

Now, we could add a subscription to our ``BatSignal`` node that listens for the ``"bat-signal-main"`` command and responds to the crisis however we can scale the number of Bat Signals and Bat...men(?) to any extent if we separate them. Herein lies one of the cornerstones of ``hivemind``.


First, let's create the node to host our subscription.

.. code-block:: shell

    ~$> hm create_node batman

Now, we should have the following:

.. code-block:: text

    nodes/
        `- __init__.py
        `- batman/
            `- __init__.py
            `- batman.py
        `- batsignal/
            ` - ...

Within the node definition (``nodes/batman/batman.py``) we can set up the subscription.

.. code-block:: python

    class Batman(_Node):
        # ...

        def subscriptions(self) -> None:
            """
            Stay vigilant caped crusader
            """
            self._bat_signal_subscription = self.add_subscription(
                name='bat-signal-*',
                function=self._go_save_the_day
            )


        def _go_save_the_day(self, payload) -> int:
            """
            Here, we can save the day.

            :param payload: The message data sent from a service who's name matches
                            the subscription name pattern. In this case, anything
                            matching "bat-signal-*"
            """
            if not isinstance(payload, str):
                self.log_warning(f'Unknown payload type: {type(payload)}')
                return 0

            if payload == "Batman! We need help!":
                print ('Batman has saved the day!') # To print to our stdout

            else:
                print ('Oh no! Batman doesn\'t know what to do!')

            return 0

.. _Django: https://www.djangoproject.com/
