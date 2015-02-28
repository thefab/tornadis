# tornadis

## Status (master branch)

[![Build Status](https://travis-ci.org/thefab/tornadis.png)](https://travis-ci.org/thefab/tornadis)
[![Coverage Status](https://coveralls.io/repos/thefab/tornadis/badge.png)](https://coveralls.io/r/thefab/tornadis)
[![Code Health](https://landscape.io/github/thefab/tornadis/master/landscape.png)](https://landscape.io/github/thefab/tornadis/master)
[![Requirements Status](https://requires.io/github/thefab/tornadis/requirements.png?branch=master)](https://requires.io/github/thefab/tornadis/requirements/?branch=master)

## What is it ?

`tornadis` is an async minimal redis client for tornado ioloop designed for performance (uses C hiredis parser).

**WARNING : tornadis is considered in beta quality (API can change)**

### Features

- simple
- good performances
- coroutine friendly
- production ready (timeouts, connection pool, error management)
- nearly all redis features (pipeline, pubsub, standard commands)

## Full documentation

Full documentation is available at http://tornadis.readthedocs.org

## Examples

### Tornado web handler

Let's do a blocking pop an a non-existing queue with a 3 seconds timeout so
that each request takes 3 seconds to be served:

```python
import tornado
from tornado.web import RequestHandler, Application, url
import tornadis


class GetHandler(RequestHandler):

    @tornado.gen.coroutine
    def get(self):
        client = tornadis.Client(port=6379)
        yield client.connect()
        yield client.call("BLPOP", "empty", 3)
        self.finish()


app = Application([url(r"/", GetHandler)])
app.listen(8888)
tornado.ioloop.IOLoop.current().start()
```

Now let's measure the time to complete 3 concurent requests to this service:

    $ ab -c 3 -n 3 http://localhost:8888/ | grep 'Time taken'
    Time taken for tests:   3.032 seconds

As you can see the requests are processed in parallel because Tornadis doesn't block the Tornado event loop while it waits for a response.

### Standalone script

This example demonstrates how to make parallel requests outside of a web context using Tornado's IO loop:

```python
from datetime import datetime
import tornado
import tornadis


def log(message):
    print datetime.now().strftime("%H:%M:%S") + ": " + message


@tornado.gen.coroutine
def time_consuming_function():
    log("blocking pop")
    client = tornadis.Client(port=6379)
    yield client.connect()
    yield client.call("BLPOP", "empty", 3)
    log("done waiting")


def debug_future(future):
    exception = future.exception()
    if exception is not None:
        raise(exception)


loop = tornado.ioloop.IOLoop.instance()
loop.add_future(time_consuming_function(), debug_future)
loop.add_future(time_consuming_function(), debug_future)
loop.start()
```


The output shows that requests to Redis are made in parallel:

    $ python tornadis_script.py 
    14:23:41: blocking pop
    14:23:41: blocking pop
    14:23:45: done waiting
    14:23:45: done waiting

