**************
Simple Example
**************


RootController
==============

The first thing to set up before getting into individual nodes is the ``RootController``. This controller is the "brain" of hivemind. It's where we process the data feeds from our services and propagate our data to any subscriptions that require them. While there is a lot to go over here, we can start very simple and with only three lines of code.

With a new project folder created (e.g. ``mkdir ~/repo/my_hive``), let's create ``root.py``

.. code-block:: python

    from hivemind import RootController
    if __name__ == '__main__':
        RootController.exec_(logging='verbose')

That's all we need to boot our brain. We can start that now.

.. code-block:: shell

    ~$> python root.py
    [18/08/2019 11:49:13 PM - INFO ]: Serving on 9476...    

.. note::

    If you're getting import errors, odds are python can't find ``hivemind`` on your PYTHONPATH.


Service Node
============

With our root up and running, let's build a service to ship some data every few seconds. We do this by sub classing the abstract ``_Node``. In a new python file ``test_service.py``, we set up the following:

.. code-block:: python

    from hivemind import _Node

    class MyPingService(_Node):
        """ Message ship every N seconds """

        def services(self):
            """
            Overloaded from _Node to include any initial services that
            we boot our node with. Services can be turned on and off at
            any time via self.add_service() and self.remove_service()
            """
            self._ping_service = self.add_service(
                name='ping-central',
                function=self._ping_serivce_function
            )

        def _ping_serivce_function(self):
            """
            This function is called on a loop until the service
            is terminated. A simple service like this doesn't need
            to know when we terminate as the _Node and _Service will
            take care of that for us.
            """
            self._ping_service.send('a test message')

            # This is the best way to sleep a service as it can auto
            # return if the service is aborted or the node shut down
            self._ping_service.sleep_for(5.0)

            return 0

    if __name__ == '__main__':
        MyPingService.exec_(name='ping_service', logging='verbose')

There's some really nice hints in there for what each item does. We overload ``services`` to build our initial service and then send a message to the controller whenever it's required.

We start the node just like our root.

.. code-block:: shell

    ~$> python test_service.py

You should see it log a few items including the registration of the node and the service. Within the ``root.py`` terminal, you should see it interacting with the node and receiving a payload every 5 seconds.

Subscription Node
=================

Now that we have a controller to manage data and a service to produce data, let's utilize a consumer to work with the data. In ``test_subscription.py`` let's create the following:

.. code-block:: python

    class MyPingSubscription(_Node):
        """ Subscription to the ping service """

        def subscriptions(self):
            """
            Overloaded from _Node to register any subscriptions. Just 
            like services, we can add and remove at whim.
            """
            self._my_subscription = self.add_subscription(
                'ping-central',
                self._receive_message
            )

        def _receive_message(self, payload: str):
            """
            This is an endpoint that gets fired when our controller
            forwards payloads.
            """
            if not isinstance(payload, str):
                return
            print (payload.upper())

    if __name__ == '__main__':
        MyPingSubscription.exec_(name='ping_sub', logging='verbose')

Once done, we are ready to fire up this node and complete the cycle.

.. code-block:: shell

    ~$> python test_subscription.py

If all goes well you should see the subscription printing out ``"A TEST MESSAGE"`` every 5 seconds.
