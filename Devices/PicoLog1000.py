import time

import numpy
from tango import AttrQuality

from Devices.AdlinkADC import AdlinkADC
from Devices.ChannelADC import ChannelADC
from Devices.TangoAttribute import TangoAttribute


class PicoLog1000(AdlinkADC):
    def __init__(self, tango_device_name, folder=None, **kwargs):
        super().__init__(tango_device_name, folder=folder, **kwargs)
        self.x = None
        self.shot = 0

    def activate(self):
        if not super().activate():
            return False
        rearm = self.kwargs.get('rearm', False)
        if not rearm:
            return True
        record_in_progress = self.device.read_attribute('record_in_progress')
        if record_in_progress.quality != AttrQuality.ATTR_VALID or record_in_progress.value:
            self.logger.warning(f'{self.device_name} Record in progress - can not rearm')
            return False
        self.device.wrire_attribute('record_in_progress', True)
        self.logger.debug(f'{self.device_name} Rearmed')
        return True

    def read_shot(self):
        # read data ready
        data_ready = self.device.read_attribute('data_ready')
        if data_ready.quality != AttrQuality.ATTR_VALID or not data_ready.value:
            return self.shot
        return self.shot + 1

    def read_shot_time(self):
        return time.time()

    def save(self, log_file, zip_file, folder=None):
        trigger = self.kwargs.get('trigger', 'save')
        if trigger != 'save' and trigger != 'ignore':
            return
        if folder is None:
            folder = self.folder
        if not folder.endswith('/'):
            folder += '/'
        # read data ready
        data_ready = self.device.read_attribute('data_ready')
        if data_ready.quality != AttrQuality.ATTR_VALID or not data_ready.value:
            self.logger.warning("%s data is not ready" % self.device_name)
            return False
        # read channels list
        channels = self.device.read_attribute('channels').value
        channels_list = []
        try:
            channels_list = eval(channels)
        except KeyboardInterrupt:
            raise
        except:
            pass
        if len(channels_list) <= 0:
            self.logger.warning("%s empty channels list" % self.device_name)
            return False
        # read other attributes
        trigger = self.device.read_attribute('trigger').value
        sampling = self.device.read_attribute('sampling').value
        points = self.device.read_attribute('points_per_channel').value
        try:
            stop_time = self.device.read_attribute('stop_time')
            if stop_time.quality != AttrQuality.ATTR_VALID:
                self.properties['trigger_time'] = [str(stop_time.value - points*sampling)]
        except KeyboardInterrupt:
            raise
        except:
            pass
        # generate times array
        times = numpy.linspace(0, (points - 1) * sampling, points, dtype=numpy.float64)
        if trigger < points:
            trigger_offset = times[trigger]
            times -= trigger_offset
        # save channels properties and data
        for i in channels_list:
            chan = ChannelADC(self.device_name, 'chany%02i'%i, folder)
            if not chan.activate():
                continue
            chan.read_properties()
            TangoAttribute.read_attribute(chan)
            chan.x_attr.value = times + (i * sampling / len(channels_list))
            chan.save_properties(zip_file, folder=folder)
            chan.save_log(log_file)
            chan.save_data(zip_file, folder=folder)
