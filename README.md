# tornadis

## Status (master branch)

[![Travis](https://img.shields.io/travis/thefab/tornadis.svg)](https://travis-ci.org/thefab/tornadis)
[![Coverage Status](https://coveralls.io/repos/thefab/tornadis/badge.png)](https://coveralls.io/r/thefab/tornadis)
[![Code Health](https://landscape.io/github/thefab/tornadis/master/landscape.png)](https://landscape.io/github/thefab/tornadis/master)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/thefab/docker-centos-opinionated/blob/master/LICENSE)
[![Maturity](https://img.shields.io/badge/maturity-beta-yellow.svg)](https://github.com/thefab/docker-centos-opinionated)
[![Maintenance](https://img.shields.io/maintenance/yes/2018.svg)](https://github.com/thefab)

## What is it ?

`tornadis` is an async minimal redis client for tornado ioloop designed for performance (uses C hiredis parser).

**WARNING : tornadis is considered in beta quality (API can change)**

### Features

- simple
- good performances
- coroutine friendly
- production ready (timeouts, connection pool, error management)
- nearly all redis features (pipeline, pubsub, standard commands)
- autoconnection, autoreconnection
- Python2 (>=2.7) and Python3 (>=3.2) support
- Tornado >=4.2 (in master branch) and Tornado 4.1 + toro (in tornado41 branch) support

### Not implemented

- cluster support

## Example

```python
# Let's import tornado and tornadis
import tornado
import tornadis


@tornado.gen.coroutine
def talk_to_redis():
    # let's (re)connect (autoconnect mode), call the ping redis command
    # and wait the reply without blocking the tornado ioloop
    # Note: call() method on Client instance returns a Future object (and
    # should be used as a coroutine).
    result = yield client.call("PING")
    if isinstance(result, tornadis.TornadisException):
        # For specific reasons, tornadis nearly never raises any exception
        # they are returned as result
        print "got exception: %s" % result
    else:
        # result is already a python object (a string in this simple example)
        print "Result: %s" % result


# Build a tornadis.Client object with some options as kwargs
# host: redis host to connect
# port: redis port to connect
# autoconnect=True: put the Client object in auto(re)connect mode
client = tornadis.Client(host="localhost", port=6379, autoconnect=True)

# Start a tornado IOLoop, execute the coroutine and end the program
loop = tornado.ioloop.IOLoop.instance()
loop.run_sync(talk_to_redis)
```

## Full documentation

Full documentation is available at http://tornadis.readthedocs.org
