# tornadis

## Status (master branch)

[![Build Status](https://travis-ci.org/thefab/tornadis.png)](https://travis-ci.org/thefab/tornadis)
[![Coverage Status](https://coveralls.io/repos/thefab/tornadis/badge.png)](https://coveralls.io/r/thefab/tornadis)
[![Code Health](https://landscape.io/github/thefab/tornadis/master/landscape.png)](https://landscape.io/github/thefab/tornadis/master)
[![Requirements Status](https://requires.io/github/thefab/tornadis/requirements.png?branch=master)](https://requires.io/github/thefab/tornadis/requirements/?branch=master)

## What is it ?

`tornadis` is an async minimal redis client for tornado ioloop designed for performance (uses C hiredis parser).

**WARNING : tornadis is at an early stage of developement**

### Features

- simple
- good performance
- coroutine friendly
- production ready (timeouts, connection pool, error management)
- nearly all redis features (pipeline, pubsub, standard commands)

### Full documentation

Full documentation is available at http://tornadis.readthedocs.org
