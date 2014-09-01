#!/bin/bash

if [ "${TRAVIS_PYTHON_VERSION}" = "2.7" ]; then
  coveralls
fi
