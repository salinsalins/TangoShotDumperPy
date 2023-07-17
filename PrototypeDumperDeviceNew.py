import io
import json
import sys
import time
import logging
import zipfile
from typing import IO

import numpy
import tango
from tango import DevFailed, ConnectionFailed

sys.path.append('../TangoUtils')
from config_logger import config_logger, LOG_FORMAT_STRING_SHORT
from log_exception import log_exception


class PrototypeDumperDevice:
    TRUE_VALUES = ('true', 'on', '1', 'y', 'yes')
    FALSE_VALUES = ('false', 'off', '0', 'n', 'no')
    devices = {}

    def __init__(self, device_name: str, **kwargs):
        self.device_name = device_name
        self.kwargs = kwargs
        self.logger = config_logger()
        self.active = False
        self.device = None
        self.time = 0.0
        self.activation_timeout = 10.0
        self.reactivate = kwargs.get('reactivate', True)
        self.full_name = self.device_name
        self.properties = {}

    def new_shot(self):
        return False

    def activate(self):
        if self.active:
            return True
        if self.device_name in self.devices:
            self.active = True
            self.device = self.devices[self.device_name]
            self.logger.debug("Reusing device %s", self.device_name)
            return True
        if (time.time() - self.time) < self.activation_timeout:
            self.logger.debug("%s activation timeout", self.device_name)
            return False
        if not self.reactivate:
            return False
        self.device = None
        self.active = False
        try:
            self.device = tango.DeviceProxy(self.device_name)
            self.active = True
            self.devices[self.device_name] = self.device
            self.logger.debug("Device %s has been activated", self.device_name)
            return True
        except ConnectionFailed:
            log_exception("%s connection failed ", self.device_name)
        except DevFailed as ex_value:
            if 'DeviceNotDefined' in ex_value.args[0].reason:
                self.logger.error('Device %s is not defined in DataBase', self.device_name)
                self.reactivate = False
            else:
                log_exception("%s activation error %s", self.full_name, ex_value.args[0].reason)
        except KeyboardInterrupt:
            raise
        except:
            self.reactivate = False
            log_exception("Unexpected %s activation error: ", self.full_name)
        return False

    def save(self, log_file: IO, zip_file: zipfile.ZipFile, folder: str = None):
        raise NotImplemented()
        # if not self.active:
        #     self.logger.debug('Reading inactive device')
        #     return

    def property(self, prop_name: str):
        try:
            result = self.device.get_property(prop_name)[prop_name]
            if len(result) == 1:
                result = result[0]
            return result
            # return self.device.get_property(prop_name)[prop_name][0]
        except:
            return ''

    def properties(self, filter: str = '*'):
        # returns dictionary with device properties
        names = self.device.get_property_list(filter)
        return self.device.get_property(names)

    @staticmethod
    def as_boolean(value):
        value = str(value)
        if value.lower() in PrototypeDumperDevice.TRUE_VALUES:
            return True
        if value.lower() in PrototypeDumperDevice.FALSE_VALUES:
            return False
        return None

    @staticmethod
    def as_int(value):
        try:
            return int(str(value))
        except:
            return None
