#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


class Pipeline(object):
    """Pipeline class to stack redis commands.

    A pipeline object is just a kind of stack. You stack complete redis
    commands (with their corresponding arguments) inside it.

    Then, you use the call() method of a Client object to process the pipeline
    (which must be the only argument of this call() call).

    More informations on the redis side: http://redis.io/topics/pipelining

    Attributes:
        pipelined_args: A list of tuples, earch tuple is a complete
            redis command.
        number_of_stacked_calls: the number of stacked redis commands
            (integer).
    """

    def __init__(self):
        """Simple constructor."""
        self.pipelined_args = []
        self.number_of_stacked_calls = 0

    def stack_call(self, *args):
        """Stacks a redis command inside the object.

        The syntax is the same than the call() method a Client class.

        Args:
            *args: full redis command as variable length argument list.

        Examples:
            >>> pipeline = Pipeline()
            >>> pipeline.stack_call("HSET", "key", "field", "value")
            >>> pipeline.stack_call("PING")
            >>> pipeline.stack_call("INCR", "key2")
        """
        self.pipelined_args.append(args)
        self.number_of_stacked_calls = self.number_of_stacked_calls + 1
