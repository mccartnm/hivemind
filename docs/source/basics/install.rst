*******
Install
*******

Prerequisites
=============

1. Python 3.7+

Contributers
============

Environment
-----------

To set up a full development environment, it's recommended you use a virtual environment to contain anything that the package might need.


.. code-block:: shell

    ~$> python -m venv ~/virtualenv/hm

.. tip::

    ``~/virtualenv/hm`` can be any path as long as you remember where you stash it.


Any time you want to enter the virtual environment, simply source it

.. code-block:: shell

    # Unix
    ~$> source ~/virtualenv/hm/bin/activate

    #Windows
    C:\> ~\virtualenv\hm\Scripts\activate


From there, your prompt should enter the environment and alert you with a ``(hm)`` prefix.

.. code-block:: shell

    (hm) ~$> ...


To leave the environment, at any time, simply enter:

.. code-block:: shell

    (hm) ~$> deactivate
    ~$>

Git
---

Once you have a virtual environment set up, let's grab the source

.. code-block:: shell

    ~$> git clone https://github.com/mccartnm/hivemind.git

PyPi
====

Coming soon... (once available on pypi or at least ``setup.py``)

If you're really itching to try, clone the repo_ and add it to your ``PYTHONPATH``/use ``sys.path.append`` on your scripts.

.. _repo: http://github.com/mccartnm/hivemind