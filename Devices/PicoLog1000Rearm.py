from PrototypeDumperDevice import *


class PicoLog1000Rearm(PrototypeDumperDevice):

    def activate(self):
        record_in_progress = self.device.read_attribute('record_in_progress').value
        if record_in_progress:
            self.logger.warning(f'{self.name} Record in progress - can not rearm')
            return False
        self.device.wrire_attribute('record_in_progress', True)
        self.logger.debug(f'{self.name} Rearmed')
        return True

    def save(self, log_file, zip_file, folder=None):
        return True
