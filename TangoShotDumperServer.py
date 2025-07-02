#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shot dumper tango device server
A. L. Sanin, started 25.06.2021
"""
import sys, os
import time

from tango import AttrWriteType, DispLevel, DevState, AttrDataFormat
from tango.server import attribute

if os.path.realpath('../TangoUtils') not in sys.path: sys.path.append(os.path.realpath('../TangoUtils'))
from TangoServerPrototype import TangoServerPrototype
from TangoShotDumper import TangoShotDumper
from log_exception import log_exception


class TangoShotDumperServer(TangoServerPrototype):
    server_version_value = '3.6'
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

    device_list = attribute(label="device_list", dtype=[str],
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ,
                          # dformat=AttrDataFormat.SPECTRUM,
                          # unit="", format="%s",
                          max_dim_x=1000,
                          max_dim_y=0,
                          doc="Dumper device list")

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
            self.device_list_value = []
            self.pre = f'{self.name} TangoShotDumperServer'
            self.set_state(DevState.INIT, 'Initial configuration started')
            # init TangoShotDumper part
            self.dumper = TangoShotDumper(self.config.file_name)
            # set_config for TangoShotDumper part
            if self.dumper.set_config():
                self.set_state(DevState.RUNNING, 'Configured successfully')
            else:
                self.set_state(DevState.FAULT, 'Initial configuration error')
                return False
            self.device_list_value = [di.full_name for di in self.dumper.dumper_items]
            # set shot_number and short time from DB
            try:
                pr = self.get_attribute_property('shot_number', '__value')
                value = int(pr)
            except:
                value = 0
            self.dumper.write_shot_number(value)
            # set shot_time
            try:
                pr = self.get_attribute_property('shot_time', '__value')
                value = float(pr)
            except:
                value = 0.0
            self.dumper.write_shot_time(value)
        except:
            self.log_exception('Configuration set error')
            self.set_state(DevState.FAULT, 'Configuration set error')
            return False

    # def write_shot_time(self, value):
    #     self.dumper.write_shot_time(value)

    def read_shot_time(self):
        return self.dumper.read_shot_time()

    # def write_shot_number(self, value):
    #     self.dumper.write_shot_number(value)

    def read_shot_number(self):
        return self.dumper.read_shot_number()

    def read_device_list(self):
        # result = ''
        # for dev in self.dumper.dumper_items:
        #     pass
        #     result += dev.full_name
        # # if attr is not None:
        # #     attr.set_value(result)
        return self.device_list_value


def looping():
    t0 = time.time()
    for dev_name in TangoShotDumperServer.devices:
        dev = TangoShotDumperServer.devices[dev_name]
        dt = time.time() - t0
        if dt < dev.config['sleep']:
            time.sleep(dev.config['sleep'] - dt)
        try:
            # dev.logger.debug('***************** Processing %s', dev_name)
            if dev.get_state() == DevState.RUNNING:
                if dev.dumper.activate() <= 0:
                    continue
                # check for new shot
                # ns = dev.dumper.check_new_shot()
                # if not not ns:
                #     continue
                dev.set_status('Processing shot')
                dev.dumper.process()
                n = dev.read_shot_number()
                t = dev.read_shot_time()
                # dev.set_attribute_property('shot_number', '__value', n)
                # dev.set_attribute_property('shot_time', '__value', t)
                dev.set_status('Waiting for new shot')
            # msg = '%s processed' % dev.device_name
            # dev.logger.debug(msg)
            # dev.debug_stream(msg)
        except:
            log_exception()
            msg = '%s process error' % dev
            dev.logger.warning(msg)
            dev.error_stream(msg)
            dev.logger.debug('', exc_info=True)


if __name__ == "__main__":
    TangoShotDumperServer.run_server(event_loop=looping)
    # TangoShotDumperServer.run_server()
