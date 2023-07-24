import time
import zipfile

import numpy
import tango

from Devices.TangoAttribute import TangoAttribute


class TangoAttributeHistory(TangoAttribute):
    def __init__(self, device_name, attribute_name, folder=None, delta_t=120.0, **kwargs):
        super().__init__(device_name, attribute_name, folder, True, **kwargs)
        self.delta_t = delta_t
        self.full_name += '_history'
        self.t0 = 0.0
        self.relative_time = kwargs.get('relative_time', True)
        self.x = None
        self.y = None

    def read_attribute(self):
        super().read_attribute()
        if self.attr.data_format != tango.AttrDataFormat.SCALAR:
            self.logger.info("History of non SCALAR attribute %s is not supported" % self.full_name)
            return False
        period = self.device.get_attribute_poll_period(self.attribute_name)
        if period <= 0:
            self.logger.info("Attribute %s is not polled" % self.full_name)
            return False
        self.t0 = time.time()
        try:
            t0_server = self.kwargs.get('t0_server', None)
            t0_attribute = self.kwargs.get('t0_attribute', 'elapsed')
            t0_delta = self.kwargs.get('t0_delta', True)
            if t0_server:
                t0 = tango.DeviceProxy(t0_server).read_attribute(t0_attribute).value
                if t0_delta:
                   self.t0 = time.time() - t0
                else:
                   self.t0 = t0
        except KeyboardInterrupt:
            raise
        except:
            pass
        m = int(self.delta_t * 1000.0 / period + 1000)
        history = self.device.attribute_history(self.attribute_name, m)
        n = len(history)
        if n <= 0:
            self.logger.info("Empty history for %s" % self.full_name)
            return False
        y = numpy.zeros(n)
        x = numpy.zeros(n)
        for i, h in enumerate(history):
            if h.quality != tango.AttrQuality.ATTR_VALID:
                y[i] = numpy.nan
            else:
                y[i] = h.value
                x[i] = h.time.totime()
        index = numpy.logical_and(y != numpy.nan, x >= (self.t0 - self.delta_t))
        if len(y[index]) <= 0:
            self.logger.info("%s No values for %f seconds in history", self.full_name, self.delta_t)
            return False
        self.y = y[index]
        self.x = x[index] * 1000.0
        if self.relative_time:
            self.x -= self.t0 * 1000.0
        self.x_attr = history[0]
        self.x_attr.value = self.x
        return True

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        old_name = self.attribute_name
        self.attribute_name += '_history'
        old_value = self.attr.value
        self.attr.value = numpy.stack((self.x, self.y), 1)
        old_data_format = self.properties['data_format']
        self.properties['data_format'] = ['IMAGE']
        result = super().save_data(zip_file, folder)
        self.attr.value = old_value
        self.properties['data_format'] = old_data_format
        self.attribute_name = old_name
        return result

    def save_log(self, log_file, additional_marks=None):
        old_name = self.attribute_name
        self.attribute_name += '_history'
        old_value = self.attr.value
        self.attr.value = self.y
        old_data_format = self.properties['data_format']
        self.properties['data_format'] = ['SPECTRUM']
        old_label = self.properties.get('label', None)
        self.properties['label'] = [self.attribute_name]
        result = super().save_log(log_file, additional_marks)
        self.attr.value = old_value
        self.properties['data_format'] = old_data_format
        self.attribute_name = old_name
        if old_label is not None:
            self.properties['label'] = old_label
        else:
            self.properties.pop('label', [])
        return result

    def save_properties(self, zip_file, folder=''):
        old_name = self.attribute_name
        self.attribute_name += '_history'
        old_label = self.properties.get('label', None)
        self.properties['label'] = [self.attribute_name]
        result = super().save_properties(zip_file, folder)
        self.attribute_name = old_name
        if old_label is not None:
            self.properties['label'] = old_label
        else:
            self.properties.pop('label', [])
        return result
