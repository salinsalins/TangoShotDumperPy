import time

import numpy
import tango

from Devices.TangoAttribute import TangoAttribute


class TangoAttributeHistory(TangoAttribute):
    def __init__(self, device_name, attribute_name, folder=None, delta_t=120.0, **kwargs):
        super().__init__(device_name, attribute_name, folder, True, **kwargs)
        self.delta_t = delta_t
        self.full_name += '_history'

    def read_attribute(self):
        super().read_attribute()
        self.file_name = self.full_name + '_history'
        self.properties['history'] = ['True']
        if self.attr.data_format != tango.AttrDataFormat.SCALAR:
            self.logger.info("History of non SCALAR attribute %s is not supported" % self.full_name)
            return False
        period = self.device.get_attribute_poll_period(self.attribute_name)
        if period <= 0:
            self.logger.info("Attribute %s is not polled" % self.full_name)
            return False
        m = int(self.delta_t * 1000.0 / period + 10)
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
        index = numpy.logical_and(y != numpy.nan, x >= (time.time() - self.delta_t))
        if len(y[index]) <= 0:
            self.logger.info("%s No values for %f seconds in history", self.full_name, self.delta_t)
            return False
        # self.y = y[index]
        # self.x = x[index]
        self.attr.value = numpy.stack((x[index], y[index]), 1)
        self.properties['data_format'] = ['IMAGE']

