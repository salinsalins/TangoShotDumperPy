import time, io, os
import zipfile

from PrototypeDumperDevice import PrototypeDumperDevice
from log_exception import log_exception


class DelayedDevice(PrototypeDumperDevice):
    def __init__(self, parent, delay=0.0, *args, **kwargs):
        super().__init__(parent.device_name, *args, **kwargs)
        self.save_list = []
        self.parent = parent
        self.delay = delay

    def save(self, log_file, zip_file, folder=None):
        zip_file_name = zip_file.filename
        log_file_name = log_file.buffer.name
        log_file_position = log_file.tell()
        self.save_list.append((time.time(), zip_file, log_file, folder,
                               zip_file_name, log_file_name, log_file_position))
        self.logger.debug('Save at %s', time.time())
        return True

    def activate(self):
        self.active = True
        try:
            if self.save_list:
                t = self.save_list[0][0]
                if time.time() - t >= self.delay:
                    self.logger.debug('Delayed save after %s s', time.time() - t)
                    item = self.save_list.pop(0)
                    zip = item[1].filename
                    log = item[2].buffer.name
                    folder = item[3]
                    pos = item[6]
                    # save data to file
                    # log_file = open(log, 'wb', encoding='cp1251')
                    # log_file = open('test.log', 'a', encoding='cp1251')
                    text_buffer = io.StringIO()
                    zip_file = zipfile.ZipFile(zip, 'a', compression=zipfile.ZIP_DEFLATED)
                    self.parent.save(text_buffer, zip_file, folder)
                    zip_file.close()
                    # log_file.close()
                    # correct log file
                    fs = os.path.getsize(log)
                    log_file = open(log, 'rb')
                    log_file.seek(pos)
                    tail = log_file.read()
                    log_file.close()
                    log_file = open(log, 'rb+')
                    log_file.seek(pos)
                    log_file.write(text_buffer.getvalue().encode())
                    log_file.write(tail)
                    log_file.close()
        except:
            log_exception()
            return False
        return True

