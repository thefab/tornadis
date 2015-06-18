# CHANGES

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
