#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stand-alone version of Tango dumper
A. L. Sanin, started 07.09.2021
"""
import datetime
import logging
import os
import sys
import time
import zipfile

from Terminal import CONFIG_FILE

if os.path.realpath('../TangoUtils') not in sys.path: sys.path.append(os.path.realpath('../TangoUtils'))
from Configuration import Configuration
from config_logger import config_logger, LOG_FORMAT_STRING_SHORT
from log_exception import log_exception

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'Tango Shot Dumper'
APPLICATION_NAME_SHORT = os.path.basename(__file__).replace('.py', '')
APPLICATION_VERSION = '3.6'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

# import all modules from .\Devices folder
folder_name = 'Devices'
for filename in os.listdir(folder_name):
    # Process all python files in a directory that don't start
    # with underscore (which also prevents this module from
    # importing itself).
    if filename.startswith('_'):
        continue
    fns = filename.split('.')
    if fns[-1] in ('py', 'pyw'):
        module_name = fns[0]
        try:
            exec(f'from {folder_name}.{module_name} import {module_name} as {module_name}')
        except:
            log_exception(f'Error during import from {folder_name}.{module_name}')
del fns, filename, module_name, folder_name

DEFAULT_CONFIG = {"sleep": 1.0, 'log_level': logging.DEBUG, "out_root_dir": '.\\data\\',
                  "shot_number": 1, "shot_time": 0.0, "devices": []
                  }


class TangoShotDumper:
    _version = APPLICATION_VERSION
    _name = APPLICATION_NAME

    def __init__(self, config_file_name=None, log_level=logging.INFO):
        self.logger = config_logger(format_string=LOG_FORMAT_STRING_SHORT, level=log_level)
        self.log_file = None
        self.zip_file = None
        self.out_dir = None
        self.locked = False
        self.lock_file = None
        if config_file_name is None:
            config_file_name = CONFIG_FILE
        self.config_file_name = config_file_name
        # default config
        self.config = Configuration(self.config_file_name, DEFAULT_CONFIG)
        self.out_root_dir = self.config.get("out_root_dir", "D:\\data\\")
        self.shot_number_value = self.config.get("shot_number", 84892)
        self.shot_time_value = self.config.get("shot_time", 0.0)
        self.save = self.config.get("save", 'all')
        self.dumper_items = []
        self.device_groups = {}
        self.active = set()
        self.inactive = set()

    def read_shot_number(self):
        return self.shot_number_value

    def write_shot_number(self, value):
        self.shot_number_value = value
        self.config['shot_number'] = value

    def read_shot_time(self):
        return self.shot_time_value

    def write_shot_time(self, value=None):
        if value is None:
            value = time.time()
        self.shot_time_value = value
        self.config['shot_time'] = value

    def set_config(self):
        file_name = self.config.file_name
        if file_name is None:
            file_name = ''
        try:
            # set log level
            self.logger.setLevel(self.config.get('log_level', logging.DEBUG))
            self.logger.debug('Log level has been set to %s',
                              logging.getLevelName(self.logger.getEffectiveLevel()))
            self.config["sleep"] = self.config.get("sleep", 1.0)
            self.out_root_dir = self.config.get("out_root_dir", '.\\data\\')
            self.write_shot_number(self.config.get("shot_number", 1))
            self.write_shot_time(self.config.get("shot_time", time.time()))
            # Restore devices
            devices = self.config.get("devices", [])
            if len(devices) <= 0:
                self.logger.error("No devices declared")
                return False
            self.dumper_items = []
            self.device_groups = {}
            for device in devices:
                try:
                    if 'exec' in device:
                        exec(device["exec"])
                    if 'eval' in device:
                        item = eval(device["eval"])
                        item.logger = self.logger
                        # self.dumper_items.append(item)
                        if item.device_name not in self.device_groups:
                            self.device_groups[item.device_name] = {}
                        if item.full_name in self.device_groups[item.device_name]:
                            self.logger.warning(f'Duplicate declaration of {item.full_name} - Ignored')
                        else:
                            self.device_groups[item.device_name][item.full_name] = item
                            self.dumper_items.append(item)
                            self.logger.info("%s has been added" % item.full_name)
                    else:
                        self.logger.warning("No 'eval' for %s" % device)
                except KeyboardInterrupt:
                    raise
                except:
                    log_exception(self, "%s creation error", str(device), level=logging.WARNING)
            if len(self.dumper_items) > 0:
                self.logger.info('%d dumper devices has been configured', len(self.dumper_items))
                return True
            else:
                self.logger.error('No dumper devices has been configured')
                return False
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, 'Configuration set error for %s', file_name, level=logging.WARNING)
            return False

    def write_config(self, file_name=None):
        try:
            self.config.write(file_name)
            self.logger.debug('Configuration saved to %s', self.config.file_name)
            return True
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, 'Configuration save error to %s', file_name)
            return False

    def activate(self):
        n = 0
        for item in self.dumper_items:
            try:
                if item.activate():
                    n += 1
                    self.active.add(item)
                    if item in self.inactive:
                        self.inactive.remove(item)
                else:
                    if item in self.active:
                        self.active.remove(item)
                    self.inactive.add(item)
            except KeyboardInterrupt:
                raise
            except:
                log_exception(self, "%s activation error", item.device_name)
        return n

    def check_new_shot(self):
        for item in self.active:
        # for item in self.dumper_items:
            try:
                t = item.new_shot()
                if t:
                    if not isinstance(t, float):
                        t = time.time()
                    self.write_shot_time(t)
                    self.shot_number_value += 1
                    self.write_shot_number(self.shot_number_value)
                    return item
            except KeyboardInterrupt:
                raise
            except:
                log_exception(self, "Error checking new shot for %s", item.device_name)
        return None

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
        except KeyboardInterrupt:
            raise
        except:
            self.logger.warning("Can not create output folder %s", of)
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

    def open_log_file(self, folder: str = ''):
        log_file = open(os.path.join(folder, self.get_log_file_name()), 'a', encoding='cp1251')
        return log_file

    @staticmethod
    def get_log_file_name():
        file_name = datetime.datetime.today().strftime('%Y-%m-%d.log')
        return file_name

    @staticmethod
    def open_zip_file(folder):
        fn = datetime.datetime.today().strftime('%Y-%m-%d_%H%M%S.zip')
        zip_file_name = os.path.join(folder, fn)
        zip_file = zipfile.ZipFile(zip_file_name, 'a', compression=zipfile.ZIP_DEFLATED)
        return zip_file

    def process(self):
        try:
            # activate items in self.dumper_items
            if self.activate() <= 0:
                self.logger.info("No active devices")
                return
            # check for new shot
            nsd = self.check_new_shot()
            if not nsd:
                return
            # new shot - save signals
            dts = self.date_time_stamp()
            self.config['shot_dts'] = dts
            print("\r\n\n***** %s New Shot %d from %s *****" % (dts, self.shot_number_value, nsd.full_name))
            self.make_log_folder()
            self.lock_output_dir()
            self.log_file = self.open_log_file(self.out_dir)
            # Write date and time
            self.log_file.write(dts)
            # Write shot number
            self.log_file.write('; Shot=%d; Shot_time=%s' % (self.shot_number_value, self.shot_time_value))
            self.log_file.write('; Dumper_version=%s' % APPLICATION_VERSION)
            self.log_file.write('; Trigger=%s' % nsd.full_name)
            # Open zip file
            self.zip_file = self.open_zip_file(self.out_dir)
            # for item in self.dumper_items:
            for device in self.device_groups:
                t0 = time.time()
                print("Saving from %s" % device)
                count = 0
                for item_name in self.device_groups[device]:
                    item = self.device_groups[device][item_name]
                    if item.active:
                        try:
                            if self.save == 'debug':
                                self.log_file.write('; %s' % item.full_name)
                                print('item:', item.full_name)
                            else:
                                item.save(self.log_file, self.zip_file)
                            count += 1
                        except KeyboardInterrupt:
                            raise
                        except:
                            log_exception(self.logger, "Exception saving %s", str(item), no_info=False)
                if count == 0:
                    print('    ** No signals dumped **')
                self.logger.debug(f'Total time for {device} {(time.time() - t0) * 1000:.1f} ms')
            zfn = os.path.basename(self.zip_file.filename)
            self.zip_file.close()
            self.log_file.write('; File=%s\n' % zfn)
            self.log_file.close()
            self.unlock_output_dir()
            self.write_config()
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, "Unexpected exception")
        # print("Active items: ", len(self.active), "  Inactive items: ", len(self.inactive))
        print("")
        print(self.time_stamp(), "Waiting for next shot ...")
        return


if __name__ == "__main__":
    try:
        level = int(sys.argv[1])
    except:
        level = 20
    try:
        config = int(sys.argv[2])
    except:
        config = CONFIG_FILE
    tsd = TangoShotDumper(config, log_level=level)
    if tsd.set_config():
        t0 = time.time()
        while True:
            time.sleep(tsd.config['sleep'])
            try:
                tsd.process()
            except KeyboardInterrupt:
                raise
            except:
                log_exception(tsd, "%s Process exception", tsd)
    else:
        tsd.logger.error('set_config returns False')
