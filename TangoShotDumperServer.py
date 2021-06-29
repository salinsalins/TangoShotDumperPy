#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shot dumper tango device server
A. L. Sanin, started 25.06.2021
"""
import datetime
import logging
import os
import sys
import time
import json
import zipfile

import tango
from tango import DevState
from tango.server import Device

NaN = float('nan')


class TangoShotDumperServer(Device):
    version = '1.0'
    server_device_list = []

    def init_device(self):
        # set default properties
        self.logger = self.config_logger(name=__name__, level=logging.DEBUG)
        self.device_proxy = tango.DeviceProxy(self.get_name())
        self.log_file = None
        self.zip_file = None
        self.out_root_dir = '.\\data\\'
        self.out_dir = None
        self.locked = False
        # read config
        try:
            self.set_state(DevState.INIT)
            # read config from device properties
            level = self.get_device_property('log_level', logging.DEBUG)
            self.logger.setLevel(level)
            # read config from file
            self.config_file = self.get_device_property('config_file', 'ShotDumperPy.json')
            self.read_config(self.config_file)
            # devices = self.get_device_property('devices', '{}')
            if self not in TangoShotDumperServer.server_device_list:
                TangoShotDumperServer.server_device_list.append(self)
        except:
            msg = 'Exception in TangoShotDumprServer'
            self.logger.error(msg)
            self.error_stream(msg)
            self.logger.debug('', exc_info=True)
            self.set_state(DevState.FAULT)

    def get_device_property(self, prop: str, default=None):
        try:
            #self.assert_proxy()
            pr = self.device_proxy.get_property(prop)[prop]
            result = None
            if len(pr) > 0:
                result = pr[0]
            if default is None:
                return result
            if result is None or result == '':
                result = default
            else:
                result = type(default)(result)
        except:
            self.logger.debug('Error reading property %s for %s', prop, self.name)
            result = default
        return result

    def set_device_property(self, prop: str, value: str):
        try:
            #self.assert_proxy()
            self.device_proxy.put_property({prop: value})
        except:
            self.logger.info('Error writing property %s for %s', prop, self.device_name)
            self.logger.debug('', exc_info=True)

    @staticmethod
    def config_logger(name: str = __name__, level: int = logging.DEBUG):
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.propagate = False
            logger.setLevel(level)
            f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
            log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            logger.addHandler(console_handler)
        return logger

    def read_config(self, file_name):
        try:
            # Read config from file
            with open(file_name, 'r') as configfile:
                s = configfile.read()
            self.config = json.loads(s)
            # Restore log level
            self.logger.setLevel(self.config.get('log_level', logging.DEBUG))
            self.logger.log(logging.DEBUG, "Log level set to %d" % self.logger.level)
            self.config["sleep"] = float(self.config.get("sleep", 1.0))
            self.out_root_dir = self.config.get("out_root_dir", '.\\data\\')
            self.shot = self.config.get('shot', 0)
            # Restore devices
            items = self.config.get("devices", [])
            self.device_list = []
            if len(items) <= 0:
                self.logger.error("No devices declared")
                return False
            for unit in items:
                try:
                    if 'exec' in unit:
                        exec(unit["exec"])
                    if 'eval' in unit:
                        item = eval(unit["eval"])
                        self.device_list.append(item)
                        self.logger.info("%s has been added" % unit["eval"])
                    else:
                        self.logger.info("No 'eval' option for %s" % unit)
                except:
                    self.logger.warning("Error in %s initialization" % str(unit))
                    self.logger.debug('', exc_info=True)
            self.logger.info('Configuration restored from %s' % file_name)
            return True
        except:
            self.logger.info('Configuration restore error from %s' % file_name)
            self.logger.debug('', exc_info=True)
            return False

    def write_config(self, file_name):
        try:
            self.config['shot'] = self.shot
            with open(file_name, 'w') as configfile:
                configfile.write(json.dumps(self.config, indent=4))
            self.logger.info('Configuration saved to %s' % file_name)
        except:
            self.logger.info('Configuration save error to %s' % file_name)
            self.logger.debug('', exc_info=True)
            return False

    def activate(self):
        for item in self.device_list:
            try:
                item.activate()
            except:
                self.server_device_list.remove(item)
                self.logger.error("%s activation error", item)
                self.logger.debug('', exc_info=True)

    def check_new_shot(self):
        for item in self.device_list:
            try:
                if item.new_shot():
                    return True
            except:
                # self.device_list.remove(item)
                self.logger.error("%s check for new shot", item)
                self.logger.debug('', exc_info=True)
        return False

    @staticmethod
    def date_time_stamp():
        return datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def time_stamp():
        return datetime.datetime.today().strftime('%H:%M:%S')

    @staticmethod
    def get_log_folder():
        ydf = datetime.datetime.today().strftime('%Y')
        mdf = datetime.datetime.today().strftime('%Y-%m')
        ddf = datetime.datetime.today().strftime('%Y-%m-%d')
        folder = os.path.join(ydf, mdf, ddf)
        return folder

    def make_log_folder(self):
        of = os.path.join(self.out_root_dir, self.get_log_folder())
        try:
            if not os.path.exists(of):
                os.makedirs(of)
                self.logger.debug("Output folder %s has been created", of)
            self.out_dir = of
            return True
        except:
            self.logger.debug("Can not create output folder %s", of)
            self.out_dir = None
            return False

    def lock_output_dir(self, folder=None):
        if folder is None:
            folder = self.out_dir
        if self.locked:
            self.logger.warning("Unexpected lock")
            self.zip_file.close()
            self.log_file.close()
            self.unlock_output_dir()
        self.lock_file = open(os.path.join(folder, "lock.lock"), 'w+')
        self.locked = True
        self.logger.debug("Directory %s locked", folder)

    def unlock_output_dir(self):
        if self.lock_file is not None:
           self.lock_file.close()
           os.remove(self.lock_file.name)
        self.locked = False
        self.lock_file = None
        self.logger.debug("Directory unlocked")

    def open_log_file(self, folder=''):
        logf = open(os.path.join(folder, self.get_log_file_name()), 'a')
        return logf

    @staticmethod
    def get_log_file_name():
        logfn = datetime.datetime.today().strftime('%Y-%m-%d.log')
        return logfn

    @staticmethod
    def open_zip_file(folder):
        fn = datetime.datetime.today().strftime('%Y-%m-%d_%H%M%S.zip')
        zip_file_name = os.path.join(folder, fn)
        zip_file = zipfile.ZipFile(zip_file_name, 'a', compression=zipfile.ZIP_DEFLATED)
        return zip_file

    def process(self):
        # Activate items in devices_list
        self.activate()
        if len(self.server_device_list) <= 0:
            self.logger.error("No active devices")
            return
        try:
            self.activate()
            if not self.check_new_shot():
                return
            dts = self.date_time_stamp()
            self.shot += 1
            self.config['shot'] = self.shot
            self.config['shot_time'] = dts
            print("\r\n%s New Shot %d" % (dts, self.shot))
            self.make_log_folder()
            self.lock_output_dir()
            self.log_file = self.open_log_file(self.out_dir)
            # Write date and time
            self.log_file.write(dts)
            # Write shot number
            self.log_file.write('; Shot=%d' % self.shot)
            # Open zip file
            self.zip_file = self.open_zip_file(self.out_dir)
            for item in self.device_list:
                print("Saving %s" % item.name)
                try:
                    item.save(self.log_file, self.zip_file)
                except:
                    self.logger.error("Exception saving %s" % str(item))
                    self.logger.debug('', exc_info=True)
            zfn = os.path.basename(self.zip_file.filename)
            self.zip_file.close()
            self.log_file.write('; File=%s' % zfn)
            self.log_file.write('\n')
            self.log_file.close()
            self.unlock_output_dir()
            self.write_config(self.config_file)
            print("%s Waiting for next shot ...\r\n" % self.time_stamp())
        except:
            self.logger.error("Unexpected exception")
            self.logger.debug('', exc_info=True)
        return


def looping():
    print("%s Waiting for next shot ..." % TangoShotDumperServer.time_stamp())
    for dev in TangoShotDumperServer.server_device_list:
        time.sleep(dev.config['sleep'])
        try:
            dev.process()
            msg = '%s processed' % dev
            dev.logger.debug(msg)
            dev.info_stream(msg)
        except:
            msg = '%s procession error' % dev
            dev.logger.warning(msg)
            dev.error_stream(msg)
            dev.logger.debug('', exc_info=True)


if __name__ == "__main__":
    TangoShotDumperServer.run_server(event_loop=looping)
