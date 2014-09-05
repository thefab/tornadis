#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


class Pipeline(object):

    pipelined_args = None
    number_of_stacked_calls = None

    def __init__(self):
        self.pipelined_args = []
        self.number_of_stacked_calls = 0

    def stack_call(self, *args):
        self.pipelined_args.append(args)
        self.number_of_stacked_calls = self.number_of_stacked_calls + 1
