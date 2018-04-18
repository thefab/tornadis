#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import sys
from setuptools import setup, find_packages

DESCRIPTION = "tornadis is an async minimal redis client for tornado " \
              "ioloop designed for performances (use C hiredis parser)"

try:
    with open('PIP.rst') as f:
        LONG_DESCRIPTION = f.read()
except IOError:
    LONG_DESCRIPTION = DESCRIPTION

with open('requirements.txt') as reqs:
    install_requires = [
        line for line in reqs.read().split('\n')
        if (line and not line.startswith('--')) and (";" not in line)]

if sys.version_info[:2] == (3, 2):
    install_requires.append("tornado>=4.2,<4.4")
elif sys.version_info[:2] == (3, 3):
    install_requires.append("tornado>=4.2,<5.0")
else:
    install_requires.append("tornado>=4.2")

setup(
    name='tornadis',
    version="0.8.1",
    author="Fabien MARTY",
    author_email="fabien.marty@gmail.com",
    url="https://github.com/thefab/tornadis",
    packages=find_packages(),
    license='MIT',
    download_url='https://github.com/thefab/tornadis',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
        'Topic :: System :: Distributed Computing',
        'Topic :: Software Development',
    ],
    entry_points="""
    [console_scripts]
    tornadis-benchmark = tornadis.benchmark:main
    """,
)
