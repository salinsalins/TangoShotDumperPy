#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shot dumper tango device server
A. L. Sanin, started 25.06.2021
"""
import sys
import time

from tango import AttrQuality, AttrWriteType, DispLevel, DevState
from tango.server import Device, attribute, command, pipe, device_property

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')
from TangoServerPrototype import TangoServerPrototype
from TangoShotDumper import TangoShotDumper
from log_exception import log_exception


class TangoShotDumperServer(TangoServerPrototype):
    server_version_value = '2.0'
    server_name_value = 'Tango Shot Dumper Server'

    shot_number = attribute(label="last_shot_number", dtype=int,
                            display_level=DispLevel.OPERATOR,
                            access=AttrWriteType.READ,
                            unit="", format="%d",
                            doc="Last shot number")

    shot_time = attribute(label="last_shot_time", dtype=float,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ,
                          unit="s", format="%f",
                          doc="Last shot time")

    # def init_device(self):
    #     # init base class TangoServerPrototype self.set_config() will be called insight
    #     super().init_device()
    #     if self.get_state() == DevState.RUNNING:
    #         print(self.dumper.time_stamp(), "Waiting for next shot ...")
    #     else:
    #         self.logger.warning('Errors init device')
    #
    def set_config(self):
        try:
            # set_config for TangoServerPrototype part
            super().set_config()
            # set shot_number and short time from DB
            try:
                pr = self.get_attribute_property('shot_number', '__value')
                value = int(pr)
            except:
                value = 0
            self.write_shot_number(value)
            # set shot_time
            try:
                pr = self.get_attribute_property('shot_time', '__value')
                value = float(pr)
            except:
                value = 0.0
            self.write_shot_time(value)
            # init TangoShotDumper part
            self.dumper = TangoShotDumper(self.config.file_name)
            # set_config for TangoShotDumper part
            if self.dumper.set_config():
                self.set_state(DevState.RUNNING, 'Configured successfully')
                return True
            else:
                self.set_state(DevState.FAULT, 'Initial configuration error')
                return False
        except:
            log_exception('Configuration set error for %s', self.config.file_name)
            self.set_state(DevState.FAULT)
            return False

    # def write_shot_time(self, value):
    #     self.dumper.write_shot_time(value)

    def read_shot_time(self):
        return self.dumper.read_shot_time()

    # def write_shot_number(self, value):
    #     self.dumper.write_shot_number(value)

    def read_shot_number(self):
        return self.dumper.read_shot_number()


def looping():
    t0 = time.time()
    for dev in TangoShotDumperServer.device_list:
        dt = time.time() - t0
        if dt < dev.config['sleep']:
            time.sleep(dev.config['sleep'] - dt)
        try:
            if dev.get_state() == DevState.RUNNING:
                if dev.activate() <= 0:
                    continue
                # check for new shot
                if not dev.check_new_shot():
                    continue
                dev.set_status('Processing shot')
                dev.dumper.process()
                dev.set_status('Waiting new shot')
            # msg = '%s processed' % dev.device_name
            # dev.logger.debug(msg)
            # dev.debug_stream(msg)
        except:
            msg = '%s process error' % dev
            dev.logger.warning(msg)
            dev.error_stream(msg)
            dev.logger.debug('', exc_info=True)


if __name__ == "__main__":
    TangoShotDumperServer.run_server(event_loop=looping)
