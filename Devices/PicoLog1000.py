from PrototypeDumperDevice import *


class PicoLog1000(PrototypeDumperDevice):

    def activate(self):
        data_ready = self.device.read_attribute('data_ready').value
        return True

    def save(self, log_file, zip_file, folder=None):
        return True
