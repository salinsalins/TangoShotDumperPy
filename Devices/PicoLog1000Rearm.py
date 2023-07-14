from Devices.PicoLog1000 import PicoLog1000
from PrototypeDumperDevice import *


class PicoLog1000Rearm(PicoLog1000):

    def activate(self):
        record_in_progress = self.device.read_attribute('record_in_progress').value
        if record_in_progress:
            self.logger.warning(f'{self.device_name} Record in progress - can not rearm')
            return False
        self.device.wrire_attribute('record_in_progress', True)
        self.logger.debug(f'{self.device_name} Rearmed')
        return True
