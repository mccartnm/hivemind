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

    (hm) ~$> git clone https://github.com/mccartnm/hivemind.git


requirements.txt
----------------

With the code cloned, grab the development packages.

.. code-block:: shell

    (hm) ~$> cd hivemind
    (hm) ~$> pip install -r requirements/development.txt
    # ...

That should install the required thirdparty libraries. It may take a moment to grab them all. Any time a package dependency changes, you should be able to run that same command to upgrade/install the changes.

pip
---

With the code available and the developer packages at your disposal, let's install (with symlinks) to set up the CLI for us.

.. code-block:: shell

    (hm) ~$> pip install -e .


.. warning::

    The ``-e`` is important! Otherwise you may not see your changes reflected as you work.


Once that's done, you should be able to run the ``hm`` command and see the help print out.


PyPi (Non Contributers)
========================

Coming soon... (once available on pypi or at least ``setup.py``)
