import logging

from tango import AttrQuality

from PrototypeDumperDevice import *


class AdlinkADC(PrototypeDumperDevice):
    def __init__(self, device_name='binp/nbi/adc0', folder="", **kwargs):
        super().__init__(device_name, **kwargs)
        self.shot_time = 1.0
        self.folder = folder
        self.shot = -7
        self.shot = self.read_shot()

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
        ns = self.read_shot()
        if ns < 0:
            return False
        if self.shot == ns:
            return False
        self.shot = ns
        return True

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        attributes = self.device.get_attribute_list()
        for attr in attributes:
            if "chany" in attr:
                channel = PrototypeDumperDevice.Channel(self.device, attr)
                channel.logger = self.logger
                properties = channel.read_properties()
                # save options
                sdf = self.as_boolean(properties.get("save_data", [False])[0])
                slf = self.as_boolean(properties.get("save_log", [False])[0])
                retry_count = self.as_int(properties.get("retry_count", [3])[0], 1)
                properties_saved = False
                log_saved = False
                data_saved = False
                while retry_count > 0:
                    try:
                        if sdf or slf:
                            if channel.y is None:
                                channel.read_y()
                            if channel.x is None:
                                channel.read_x()
                        # Save signal properties
                        if sdf or slf and not properties_saved:
                            if channel.save_properties(zip_file, folder):
                                properties_saved = True
                        # Save log
                        if slf and not log_saved:
                            channel.save_log(log_file)
                            log_saved = True
                        # Save signal data
                        if sdf and not data_saved:
                            channel.save_data(zip_file, folder)
                            data_saved = True
                        return
                    except KeyboardInterrupt:
                        raise
                    except:
                        log_exception("%s channel save exception", self.device_name, level=logging.WARNING)
                        retry_count -= 1
                    if retry_count == 0:
                        self.logger.warning("Error reading %s" % self.device_name)
                        return
