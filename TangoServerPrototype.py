#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shot dumper tango device server
A. L. Sanin, started 05.07.2021
"""
import logging
import sys
import json

import numpy
import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState
from tango.server import Device, attribute, command, pipe, device_property


class TangoServerPrototype(Device):
    version = '0.0'
    device_list = []

    # shot_number = attribute(label="shot_number", dtype=int,
    #                         display_level=DispLevel.OPERATOR,
    #                         access=AttrWriteType.READ,
    #                         unit="", format="%d",
    #                         doc="Shot number")

    @command(dtype_in=int)
    def set_log_level(self, level):
        self.logger.setLevel(level)
        msg = '%s Log level set to %d' % (self.get_name(), level)
        self.logger.info(msg)
        self.info_stream(msg)

    def init_device(self):
        # set default properties
        self.logger = self.config_logger(name=__name__, level=logging.DEBUG)
        self.device_proxy = tango.DeviceProxy(self.get_name())
        self.shot_number_value = 0
        self.config = Configuration()
        # configure device
        try:
            self.set_state(DevState.INIT)
            # read config from device properties
            level = self.get_device_property('log_level', logging.DEBUG)
            self.logger.setLevel(level)
            # read config from file
            config_file = self.get_device_property('config_file', 'TangoAttributeHistoryServer.json')
            self.config = Configuration(config_file)
            self.set_config()
            # read shot number
            n = self.get_device_property('shot_number', 0)
            self.write_shot_number(n)
            if self not in TangoServerPrototype.device_list:
                TangoServerPrototype.device_list.append(self)
            self.logger.info('Device %s added', self.get_name())
        except:
            self.log_exception()
            self.set_state(DevState.FAULT)

    def log_exception(self, message=None, level=logging.ERROR):
        ex_type, ex_value, traceback = sys.exc_info()
        tail = ' %s %s' % (ex_type, ex_value)
        if message is None:
            message = 'Exception'
        message += tail
        self.logger.log(level, message)
        self.error_stream(message)
        self.logger.debug('', exc_info=True)

    # def read_shot_number(self):
    #     return self.shot_number_value
    #
    # def write_shot_number(self, value):
    #     self.set_device_property('shot_number', str(value))
    #     self.shot_number_value = value

    def get_device_property(self, prop: str, default=None):
        try:
            # self.assert_proxy()
            pr = self.device_proxy.get_property(prop)[prop]
            result = None
            if len(pr) > 0:
                result = pr[0]
            if default is None:
                return result
            if result is None or result == '':
                result = default
            else:
                result = type(default)(result)
        except:
            # self.logger.debug('Error reading property %s for %s', prop, self.name)
            result = default
        return result

    def set_device_property(self, prop: str, value: str):
        try:
            # self.assert_proxy()
            self.device_proxy.put_property({prop: value})
        except:
            self.logger.info('Error writing property %s for %s', prop, self.device_name)
            self.logger.debug('', exc_info=True)

    def property_list(self, filter: str = '*'):
        return self.device_proxy.get_property_list(filter)

    def properties(self, filter: str = '*'):
        # returns dictionary with device properties
        names = self.device_proxy.get_property_list(filter)
        return self.device_proxy.get_property(names)

    def set_config(self):
        try:
            # set log level
            self.logger.setLevel(self.config.get('log_level', logging.DEBUG))
            self.logger.debug("Log level set to %s" % self.logger.level)
            # set other server parameters
            # self.shot = self.config.get('shot', 0)
            self.logger.debug('Configuration restored from %s' % self.config.get('file_name'))
            return True
        except:
            self.logger.info('Configuration error')
            self.logger.debug('', exc_info=True)
            return False

    @staticmethod
    def config_logger(name: str = __name__, level: int = logging.DEBUG):
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.propagate = False
            logger.setLevel(level)
            f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
            log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            logger.addHandler(console_handler)
        return logger

    @staticmethod
    def convert_polling_status(p_s, name):
        result = {'period': 0, 'depth': 0}
        s1 = 'Polled attribute name = '
        s2 = 'Polling period (mS) = '
        s3 = 'Polling ring buffer depth = '
        # s4 = 'Time needed for the last attribute reading (mS) = '
        # s4 = 'Data not updated since 54 mS'
        # s6 = 'Delta between last records (in mS) = 98, 100, 101, 98'
        n1 = s1 + name
        for s in p_s:
            if s.startswith(n1):
                for ss in s.split('\n'):
                    try:
                        if ss.startswith(s2):
                            result['period'] = int(ss.replace(s2, ''))
                        elif ss.startswith(s3):
                            result['depth'] = int(ss.replace(s3, ''))
                    except:
                        pass
        return result

    @staticmethod
    def split_attribute_name(name):
        split = name.split('/')
        a_n = split[-1]
        m = -1 - len(a_n)
        d_n = name[:m]
        return d_n, a_n


def looping():
    pass


def post_init_callback():
    pass


class Configuration:
    def __init__(self, file_name=None, default=None):
        if default is None:
            default = {}
        if file_name is not None:
            if not self.read(file_name):
                self.data = default

    def get(self, name, default=None):
        try:
            result = self.data.get(name, default)
            if default is not None:
                result = type(default)(result)
        except:
            result = default
        return result

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        return

    def __contains__(self, key):
        return key in self.data

    def read(self, file_name):
        try:
            # Read config from file
            with open(file_name, 'r') as configfile:
                self.data = json.loads(configfile.read())
                self.__setitem__('file_name', file_name)
            return True
        except:
            return False

    def write(self, file_name=None):
        if file_name is None:
            file_name = self.data['file_name']
        with open(file_name, 'w') as configfile:
            configfile.write(json.dumps(self.data, indent=4))
        return True


if __name__ == "__main__":
    TangoServerPrototype.run_server(post_init_callback=post_init_callback, event_loop=looping)
