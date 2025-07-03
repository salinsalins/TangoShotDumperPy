import logging

from tango import AttrQuality

from Devices.ChannelADC import ChannelADC
from PrototypeDumperDevice import *


class DelayedDevice(PrototypeDumperDevice):
    def __init__(self, device_name=None, folder=None, delay = 0.0, **kwargs):
        if 'dev' in kwargs:
            if device_name is None:
                device_name = kwargs['dev']
        if device_name is None:
            device_name = 'binp/nbi/adc0'
        super().__init__(device_name, **kwargs)
        self.save_list = []
        self.shot_time = []
        self.zip_file = []
        self.log_file = []
        self.delay = delay
        self.folder = folder
        if folder is None:
            self.folder = device_name

    def save(self, log_file, zip_file, folder=None):
        self.save_list.append((time.time(), zip_file, log_file, folder))
        return

    def activate(self):
        if self.save_list:
            t = self.save_list[0][0]
            if time.time() - t >= self.delay:
                item = self.save_list.pop(0)
                zip = item[1]
                log = item[2]
                folder = item[3]
                # save data to file

