import sys
import time
import zipfile
from typing import IO

import numpy
import tango
from tango import DevFailed, ConnectionFailed

from PrototypeDumperDevice import PrototypeDumperDevice

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')
from config_logger import config_logger
from log_exception import log_exception


class PrototypeDumperDelayedDevice(PrototypeDumperDevice):

    def __init__(self, device_name: str, delay = 0.0, **kwargs):
        super().__init__(device_name, **kwargs)
        self.delay = delay

    def activate(self):
        stat = super().activate()
        if not stat:
            return False
        self.save()

    def new_shot(self):
        return False

    def save(self, log_file: IO, zip_file: zipfile.ZipFile, folder: str = None):
        self.log_file = log_file
        self.zip_file = zip_file
        self.trigger = True
        self.trigger_time = time.time()

    def get_property(self, prop_name: str, default=None):
        result_type = type(default)
        try:
            if prop_name in self.properties:
                result = self.properties[prop_name][0]
                if isinstance(default, bool):
                    if result.lower() in PrototypeDumperDevice.TRUE_VALUES:
                        return True
                    else:
                        return False
                else:
                        return result_type(result)
            else:
                return default
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
