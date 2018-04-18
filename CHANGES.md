# CHANGES

## Release 0.8.1

- python 3.6 support
- tornado 5 support

## Release 0.8.0

- add support for automatic db selection in Client or Pool object (thanks
to Sergey Orlov)
- fix missing doc section about ClientPool

## Release 0.7.1

- python 3.5 support in CI
- complex pip requirements to support :
    - python >= 3.2 with tornado 4.2 or tornado 4.3
    - python >= 3.3 with tornado 4.4
- fix a bug with Pool in case of connection failure (thanks to Sergey Orlov)
- cosmetic changes in README

## Release 0.7.0

- better documentation and examples
- less strict dependencies
- tornado 4.2 migration (toro inclusion)
- TornadisException base exception class is now available for use
- password authentification (thanks to jammed343)
- fix some nasty bugs in case of network or redis errors

## Release 0.6.0

- add aggressive_write option
- (potential) important API change if you use positional arguments in the
    Client constructor => please use named arguments now

## Release 0.5.0

- add tcp_nodelay option
- cleaning of dead code
- no ConnectionError raised anymore (in any case)
- copyright update

## Release 0.4.0

- new get_client_nowait method (on pool objects)
- autoclose feature (on pool objects)
- autoconnect is True by default
- return_connection_error behavior is True by default
- BREAKING CHANGE: no ConnectionError raised anymore, the ConnectionError
  is now returned (and not raised) in case of connection error.
- BREAKING CHANGE: return_connection_error option does not exist anymore
- BREAKING CHANGE: disconnect does not return a Future anymore !
- BREAKING CHANGE: connect() on an alreaydy connected Client object does not
  raise ClientError exception anymore.
- BREAKING CHANGE: connect() returns a Future with True or False as result 
  (depending on the connection success)
- BREAKING CHANGE: TornadisException object is not public anymore

## Release 0.3.0

- autoconnect feature (#8) (see autoconnect option)
- bugfix: behavior with empty pipeline (#10)
- BREAKING CHANGE: split call() method in call() (for futures) and
  async_call() (for regular callbacks) 
- BREAKING CHANGE: fix some problems in case of connection drop
  (see return_connection_error option)
- update requirements
- benchmark script is not py3 compatible

## Release 0.2.2

- fix issue #5 (typo in 0.2.1)

## Release 0.2.1

- fix a high cpu usage during blocking commands

## Release 0.2

- WriteBuffer object has now its own file
- WriteBuffer object is now public
- You can use a WriteBuffer object as a redis command argument

## Release 0.1.1

- fix a pip issue with tornado dependency

## Release 0.1.0

- first release
