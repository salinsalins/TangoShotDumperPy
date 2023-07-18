import sys
import time
import zipfile
from typing import IO

import numpy
import tango
from tango import DevFailed, ConnectionFailed

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')
from config_logger import config_logger
from log_exception import log_exception


class PrototypeDumperDevice:
    TRUE_VALUES = ('true', 'on', '1', 'y', 'yes')
    FALSE_VALUES = ('false', 'off', '0', 'n', 'no')
    devices = {}

    def __init__(self, device_name: str, **kwargs):
        self.device_name = device_name
        self.kwargs = kwargs
        self.full_name = self.device_name
        self.logger = config_logger()
        self.active = False
        self.device = None
        self.time = 0.0
        self.activation_timeout = kwargs.get('activation_timeout', 10.0)
        self.reactivate = kwargs.get('reactivate', True)
        self.properties = kwargs.get('properties', {})

    def activate(self):
        if self.active:
            return True
        if self.device_name in self.devices:
            self.device = self.devices[self.device_name]
            self.active = True
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
            log_exception("Unexpected %s activation error: ", self.full_name)
            self.reactivate = False
        return False

    def new_shot(self):
        return False

    def save(self, log_file: IO, zip_file: zipfile.ZipFile, folder: str = None):
        raise NotImplemented()
        # if not self.active:
        #     self.logger.debug('Reading inactive device')
        #     return

    def get_property(self, prop_name: str, default=None):
        result_type = type(default)
        try:
            return result_type(self.properties.get(prop_name, [''])[0])
        except:
            return default

    # def property(self, prop_name: str):
    #     try:
    #         result = self.device.get_property(prop_name)[prop_name]
    #         if len(result) == 1:
    #             result = result[0]
    #         return result
    #         # return self.device.get_property(prop_name)[prop_name][0]
    #     except:
    #         return ''

    # def properties(self, filter: str = '*'):
    #     # returns dictionary with device properties
    #     names = self.device.get_property_list(filter)
    #     return self.device.get_property(names)

    @staticmethod
    def as_boolean(value, default=False):
        value = str(value)
        if value.lower() in PrototypeDumperDevice.TRUE_VALUES:
            return True
        else:
            return default

    @staticmethod
    def as_int(value, default=0):
        try:
            return int(str(value))
        except:
            return default

    def smooth(self, array, n):
        m = int(len(array) / n)
        k = int(len(array) % n)
        if m > 0:
            sa = array[:m*n].reshape(m,n).mean(axis=1)
            if k > 0:
                sb = numpy.zeros(m+1)
                sb[:-1] = sa
                sb[-1] = sa[-k:].mean()
                return sb
        else:
            sa = array.mean()
        return sa

    def print_log(self, mark_name, mark_value, unit):
        pmn = mark_name
        # if len(pmn) > 14:
        #     pmn = mark_name[:5] + '...' + mark_name[-6:]
        # print mark value
        if abs(mark_value) >= 1000.0:
            print("  ", "%14s = %7.0f %s\r\n" % (pmn, mark_value, unit), end='')
        elif abs(mark_value) >= 100.0:
            print("  ", "%14s = %7.1f %s\r\n" % (pmn, mark_value, unit), end='')
        elif abs(mark_value) >= 10.0:
            print("  ", "%14s = %7.2f %s\r\n" % (pmn, mark_value, unit), end='')
        else:
            print("  ", "%14s = %7.3f %s\r\n" % (pmn, mark_value, unit), end='')
