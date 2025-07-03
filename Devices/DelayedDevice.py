import logging

from tango import AttrQuality

from Devices.ChannelADC import ChannelADC
from PrototypeDumperDevice import *

class MyMeta(type):
    def __init__(cls, name, bases, attrs):
        print(f"Создание класса {name}")
        super().__init__(name, bases, attrs)


class DelayedDevice(PrototypeDumperDevice):
    def __init__(self, parent, delay, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = parent
        self.save_list = []
        self.delay = delay

    def save(self, log_file, zip_file, folder=None):
        self.save_list.append((time.time(), zip_file, log_file, folder))
        return True

    def activate(self):
        if self.save_list:
            t = self.save_list[0][0]
            if time.time() - t >= self.delay:
                item = self.save_list.pop(0)
                zip = item[1]
                log = item[2]
                folder = item[3]
                # save data to file
                self.parent.save(self.parent, log, zip, folder)
        return True
