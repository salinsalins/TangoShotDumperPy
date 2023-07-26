from tango import AttrDataFormat, AttrQuality

from Devices.ChannelADC import ChannelADC
from Devices.PicoLog1000 import PicoLog1000
from Devices.TangoAttribute import *


class ChannelPicoLog(ChannelADC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_attr = DeviceAttribute()
        self.avg = kwargs.get('avg', None)

    def read_attribute(self):
        if not super().read_attribute():
            return False
        if self.attr.quality != AttrQuality.ATTR_VALID:
            self.logger.info(f'{self.full_name} INVALID attribute quality')
            return False
        if self.attr.data_format != AttrDataFormat.SPECTRUM:
            self.logger.info('Channel must be SPECTRUM')
            self.active = False
            self.reactivate = False
            return False
        try:
            trigger = self.device.read_attribute('trigger').value
            sampling = self.device.read_attribute('sampling').value
            points = self.device.read_attribute('points_per_channel').value
            # generate times array
            times = numpy.linspace(0, (points - 1) * sampling, points, dtype=numpy.float64)
            trigger_offset = 0.0
            if trigger < points:
                trigger_offset = times[trigger]
                times -= trigger_offset
            # calculate approximate trigger time
            t = PicoLog1000.read_shot_time(self)
            if t:
                self.properties['trigger_time'] = [str(t - (sampling*points - trigger_offset)/1000.0)]
            self.x_attr.value = times
            # self.x_attr.value = times + (i * sampling / len(channels_list))
            return True
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self.logger, 'Can not read %s',self.full_name)
        return False

