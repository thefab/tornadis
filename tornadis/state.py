#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.gen
import toro
import datetime


class ConnectionState(object):

    __connected = None
    __connecting = None
    __since = None
    __condition = None

    def __init__(self):
        self.__condition = toro.Condition()
        self.set_disconnected()

    def is_connected(self):
        return self.__connected

    def is_connecting(self):
        return self.__connecting

    def _state_changed(self):
        self.__since = datetime.datetime.now()
        self.__condition.notify_all()

    def set_connected(self):
        self.__connected = True
        self.__connecting = False
        self._state_changed()

    def set_connecting(self):
        self.__connected = False
        self.__connecting = True
        self._state_changed()

    def set_disconnected(self):
        self.__connected = False
        self.__connecting = False
        self._state_changed()

    def get_changed_state_future(self):
        if self.__connected:
            return tornado.gen.maybe_future(True)
        if self.__connecting:
            return self.__condition.wait()
        return tornado.gen.maybe_future(False)

    def get_last_state_change_timedelta(self):
        return datetime.datetime.now() - self.__since
