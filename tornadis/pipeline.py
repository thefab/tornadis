#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

from six.moves import range as six_range


# Thanks to http://stackoverflow.com/questions/312443/...
# ...how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in six_range(0, len(l), n):
        yield l[i:i+n]


class Pipeline(object):

    pipelined_args = None
    number_of_stacked_calls = None

    def __init__(self):
        self.pipelined_args = []
        self.number_of_stacked_calls = 0

    def stack_call(self, *args):
        self.pipelined_args.append(args)
        self.number_of_stacked_calls = self.number_of_stacked_calls + 1

    def args_generator(self):
        for x in self.pipelined_args:
            yield x
