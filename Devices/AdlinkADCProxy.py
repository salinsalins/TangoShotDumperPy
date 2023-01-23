import json
import logging

from tango import AttrQuality

from Devices.AdlinkADC import AdlinkADC
from PrototypeDumperDevice import *


class AdlinkADCProxy(AdlinkADC):
    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        attributes = self.device.read_attribute('channel_list').value
        for chan in attributes:
            channel = PrototypeDumperDevice.Channel(self.device, chan)
            channel.logger = self.logger
            p = self.device.command_inout('read_channel_properties', chan)
            channel.properties = json.loads(p.replace("'", '"'))
            sdf = self.as_boolean(channel.properties.get("save_data", [False])[0])
            slf = self.as_boolean(channel.properties.get("save_log", [False])[0])
            channel.properties["save_avg"] = ['1']
            log_saved = False
            data_saved = False
            retry_count = 3
            properties_saved = False
            while retry_count > 0:
                try:
                    channel.y = self.device.command_inout('read_channel_data', chan)
                    channel.x = self.device.command_inout('read_channel_data', chan.replace('chany', 'chanx'))
                    # Save signal properties
                    if sdf or slf and not properties_saved:
                        if channel.save_properties(zip_file, folder):
                            properties_saved = True
                    if slf and not log_saved:
                        channel.save_log(log_file)
                        log_saved = True
                    # Save signal data
                    if sdf and not data_saved:
                        channel.save_data(zip_file, folder)
                        data_saved = True
                    break
                except:
                    log_exception("%s channel save exception", self.name, level=logging.WARNING)
                    retry_count -= 1
                if retry_count == 0:
                    self.logger.warning("Error reading %s" % self.name)
