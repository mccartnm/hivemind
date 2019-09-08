Hivemind
========

.. image:: ../../resource/logo_flat_medium.png
  :height: 256px
  :align: center

The python micro service prototyping sandbox on a budget!
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The What
========

.. image:: ../../resource/basic_diagram.svg
  :height: 350px
  :width: 350px
  :align: center

A fast, effective, way to generate independent process that can communicate through a centralized control without requiring the entire network to be up at once.

The paradigm for service/subscription processes is not new. In fact, it's become quite common in utilities like RabbitMQ, ROS (Robot Operating System) and others.

``hivemind`` seeks to add a few features to that paradigm.

1. Insanely fast development throughput with little to know need to understand the "under-the-hood" components
2. Lean-and-mean data layer(s) to help organize your data without any concrete overhead
3. **(Most importantly)** - we want to make it nearly impossible to take down in production environments.

The Why
=======

.. image:: ../../resource/scale_diagram.svg
  :height: 350px
  :width: 350px
  :align: center

In the modern app arena, we often have use for very atomic level operations that need to communicate with other such atomic services. This often leads to large waterfall code or, promises, or some form of chain-reactive system. In order to create a highly independent system, we turn to service/subscription models (also known as pub-sub models) in order to keep the low level "nodes" from needing anything but themselves and a connection to a sort-of central nervous system.

This approach can take many forms and doesn't fit all use cases but it's a powerful tool for horizontally scaling your software.

.. toctree::
    :maxdepth: 2
    :caption: Quick Start

    basics/install
    quickstart/root

.. toctree::
    :maxdepth: 2
    :caption: Features

    basics/words
    basics/model


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. links

.. _grab it here: http://github.com/mccartnm/hivemind
