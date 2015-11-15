Quickstart
==========

Requirements
------------

- Python 2.7 or Python >= 3.2
- unix operating system (linux, osx...)
- a running redis server (>= 2.0)

Installation
------------

With pip_ (without pip see at then end of this document)::

    pip install tornadis

First try (coroutines)
----------------------

.. literalinclude:: ../examples/coroutines.py
    :language: python
    :linenos:

Second try (callbacks)
----------------------

.. literalinclude:: ../examples/callbacks.py
    :language: python
    :linenos:

Go further: Pipeline
----------------------

.. literalinclude:: ../examples/pipeline.py
    :language: python
    :linenos:

Installation without pip
------------------------

- install tornado_ >= 4.2
- install `python wrapper for hiredis`_
- install six_
- download and uncompress a `tornadis release`_
- run ``python setup.py install`` in the tornadis directory


.. _pip : https://pypi.python.org/pypi/pip 
.. _tornado: http://www.tornadoweb.org/
.. _python wrapper for hiredis: https://github.com/redis/hiredis-py
.. _six: https://pythonhosted.org/six/
.. _tornadis release: https://github.com/thefab/tornadis/releases
