# CHANGES

## Release 0.3.0

- autoconnect feature (#8) (see autoconnect option)
- bugfix: behaviour with empty pipeline (#10)
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
