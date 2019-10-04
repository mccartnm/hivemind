What is a Hive
==============

Well, thinking about version control and scalability, we want a somewhat-standard way for developers to create nodes, roots, tasks, etc without having tho manage _every_ file themselves. It would be beneficial to have some sort of structure to make things like a cli more potent when booting up and running these nodes.

Potential structure options like:

## Option 1

```
    myhive/
        `- nodes/
            `- mynodename.py
            `- anothernodename.py
            `- mytasknode.py
        `- config/
            `- mytasknode.yaml
        `- root/
            `- settings.py
            `- controller.py
```

|      Pros     |      Cons     |
|---|---|
| Simple and to the point |  Nodes may get crowded if there are too many |
| Good separation of dutied | Probably too simple for what we need |


This leads us to potentially:

## Option 2

```
    myhive/
        `- nodes/
            `- mynodename/
                `- mynodename.py
                `- _some_local_lib.py
            `- anothernodename/
                `- ...
            `- mytasknode/
                `- mytasknode.py
        `- config/
            `- mytasknode.yaml
        `- root/
            `- settings.py
            `- controller.py
```

With this we've added an extra layer for each node to contain various components. This, along with the settings, can help us quickly define how each node should be used.


# What this all leads to:

The interface should make it simple to have a plethora of nodes and an easy way to just fire up a bunch for development or specific instances for production-like environments. We can have the `settings.py` or something similar act as the conduit depicting what should/shouldn't be run and how we can get them there.

Essentially, for a development arena, we just have to have the Root started and then we can bring up the nodes in any order (because it's just pub/sub). Things get interesting when we talk about live communication data but we'll leave that for another day.
