import time

from PrototypeDumperDevice import PrototypeDumperDevice


class DelayedDevice(PrototypeDumperDevice):
    def __init__(self, parent, delay=0.0, *args, **kwargs):
        super().__init__(parent.device_name, *args, **kwargs)
        self.save_list = []
        self.parent = parent
        self.delay = delay

    def save(self, log_file, zip_file, folder=None):
        self.save_list.append((time.time(), zip_file, log_file, folder))
        self.logger.debug('Save at %s', time.time())
        return True

    def activate(self):
        self.active = True
        if self.save_list:
            t = self.save_list[0][0]
            if time.time() - t >= self.delay:
                item = self.save_list.pop(0)
                zip = item[1]
                log = item[2]
                folder = item[3]
                # save data to file
                self.logger.debug('Delayed save at %s', time.time())
        return True

