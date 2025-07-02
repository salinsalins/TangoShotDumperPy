import logging

from tango import AttrQuality

from Devices.ChannelADC import ChannelADC
from PrototypeDumperDevice import *


class AdlinkADC(PrototypeDumperDevice):
    def __init__(self, device_name=None, folder=None, **kwargs):
        if 'dev' in kwargs:
            if device_name is None:
                device_name = kwargs['dev']
        if device_name is None:
            device_name = 'binp/nbi/adc0'
        super().__init__(device_name, **kwargs)
        self.shot_time = 1.0
        if folder is None:
            self.folder = device_name
        else:
            self.folder = folder
        self.shot = -7
        # self.shot = self.read_shot()

    def read_shot(self):
        try:
            shot = self.device.read_attribute("Shot_id")
            if shot.quality != AttrQuality.ATTR_VALID:
                return -1
            return shot.value
        except KeyboardInterrupt:
            raise
        except:
            return -1

    def read_shot_time(self):
        t0 = time.time()
        try:
            elapsed = self.device.read_attribute('Elapsed')
            if elapsed.quality != AttrQuality.ATTR_VALID:
                return -t0
            self.shot_time = t0 - elapsed.value
            return self.shot_time
        except KeyboardInterrupt:
            raise
        except:
            return -t0

    def new_shot(self):
        trigger = self.kwargs.get('trigger', 'save')
        if trigger == 'ignore':
            return False
        ns = self.read_shot()
        if ns < 0:
            return False
        if self.shot == ns:
            return False
        if self.shot < 0:
            self.shot = ns
            return False
        self.shot = ns
        return self.read_shot_time()

    def save(self, log_file, zip_file, folder=None):
        trigger = self.kwargs.get('trigger', 'save')
        if trigger != 'save' and trigger != 'ignore':
            return
        if folder is None:
            folder = self.folder
        attributes = self.device.get_attribute_list()
        for attr in attributes:
            if "chany" in attr:
                channel = ChannelADC(self.device_name, attr, folder=folder)
                channel.logger = self.logger
                if not channel.activate():
                    continue
                channel.save(log_file, zip_file, folder=folder)
