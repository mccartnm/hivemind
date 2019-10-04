Hivemind
========

Branch | Status | Coverage
--- | --- | --
`master` | [![Build Status](https://travis-ci.org/mccartnm/hivemind.svg?branch=master)](https://travis-ci.org/mccartnm/hivemind) | [![Code Coverage](https://codecov.io/gh/mccartnm/hivemind/branch/master/graph/badge.svg)](https://codecov.io/gh/mccartnm/hivemind)
`dev` | [![Build Status](https://travis-ci.org/mccartnm/hivemind.svg?branch=dev)](https://travis-ci.org/mccartnm/hivemind) | [![Code Coverage](https://codecov.io/gh/mccartnm/hivemind/branch/dev/graph/badge.svg)](https://codecov.io/gh/mccartnm/hivemind)

[Better, less crazy docs](https://mccartnm.github.io/hivemind-docs/index.html)

A python implementation of a task managment pipeline for subscription based workers. 

It boils down to a micro service platform for python lovers.

The Basics
----------
The paradigm for service/subscription processes is not new. I just wanted to create a tiny yet mighty package that could handle some of the cruft when prototyping your next network.

There are three layers within `hivemind`.

```
            [ Data Layer ] <-- Eventually
                  |
+-----------------|-----------------------------+
|         [  Control Layer  ]                   | Network
|           |       |      |                    |
|       [ Node ] [ Node ] [ Node ]              |
+-----------------------------------------------+
```

1. The Data Layer
2. The Control Layer
3. The Node Layer

But before we get into explaining how they all connect, let's start with a quick example.

## Let's Play!
Let's create a very basic two node communication. One with a `_Service`, the other with a `_Subscription` to that service.

With hivemind installed and on your local PYTHONPATH (TODO: pip install), we create the following three files:

```py
# root.py

# What most hivemind starter kits will use
from hivemind import RootController
if __name__ == '__main__':
    RootController.exec_()
```

```py
# service_node.py

from hivemind import _Node
class SendTask(_Node):
    """ A simple service that ships out a message every few seconds """
    def services(self):
        # Register Services
        self._my_service = self.add_service(
            'my-service',
            self._send_message
        )

    def _send_message(self):
        # The Service will run them forever until being shut down
        # This sends a message every 5 seconds.
        self._my_service.send('A Message For More!')
        if not self._my_service.sleep_for(5.0):
            return 0
        return 0

if __name__ == '__main__':
    this_task = SendTask('message_task')
    this_task.run()
```

```py
# sub_node.py

class ReceiveTask(_Node):
    """ A simple node that waits for payloads from "my-service" """
    def subscriptions(self):
        # Register Subscriptions
        self._my_subscription = self.add_subscription('my-service',
                                                      self._receive_message)

    def _receive_message(self, payload: str):
        if not isinstance(payload, str):
            return
        print (payload)

if __name__ == '__main__':
    this_task = ReceiveTask('listen_task')
    this_task.run()
```

Now, in three separate terminals, we run the following:

```bash
# Terminal 1
python ./root.py
```

```bash
# Terminal 2
python ./service_node.py
```

```bash
# Terminal 3
python ./sub_node.py
```

You should now see the `sub_node.py` getting the `"A Message For More!"` every 5 seconds! You can now `Ctrl + C` and restart either of the nodes in any order and the processes should just remove themselves as information becomes available. The root node must stay alive, in the event that you shut down the root, all processes mjust be restarted. This limitation will be fixed onces the `Data Layer` becomes most substantial.

Now, let's go through those layers a bit more.

# The Data Layer
This will be a layer added in after initial functionality has been written up. It will consist of a database that contains a select control groups' identity and registration utilities. (There's a lot more planned but leaving this for now)

# The Control Layer
The control layer consits of a "manager" (eventually multiple managers) that can oversee registered nodes, their subscriptions and services, as well as dispatch messages based on the required data.

As the `Data Layer` becomes available, some of the duties will move to that but ultimately the controller is where the brain lives.

# The Node Layer
A Node is a single entity that can host any number of services and add handlers for any number of subscriptions. In optimal design, a node only ever hosts a single service but there is obviously no restriction. Each service lives on a unique thread that will do any processing required.

As you add nodes to your network the root node handles the dispatching of required information for you.

TODO... Obviously...
