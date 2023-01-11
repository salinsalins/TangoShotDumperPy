import sys
import time

from tango import DevFailed, ConnectionFailed, DeviceProxy

sys.path.append('../TangoUtils')
from config_logger import config_logger
from log_exception import log_exception


class TangoDevice:
    devices = {}

    def __init__(self, device_name: str, reactivate: bool = True):
        self.logger = config_logger()
        self.name = device_name
        self.active = False
        self.device = None
        self.time = 0.0
        self.activation_timeout = 10.0
        self.reactivate = reactivate
        self.ping = -1.0
        self.error = None

    def activate(self):
        if self.name in TangoDevice.devices:
            self.device = TangoDevice.devices[self.name].device
            self.active = TangoDevice.devices[self.name].active
            self.logger.debug("%s has been reused", self.device.name())
        if self.active:
            return True
        if time.time() - self.time < self.activation_timeout:
            # self.logger.debug('Frequent reactivation request declined')
            return False
        if self.reactivate:
            self.time = time.time()
            try:
                self.device = DeviceProxy(self.name)
                self.ping = self.device.ping()
                TangoDevice.devices[self.name] = self
                self.active = True
                self.error =  None
                self.logger.debug("%s has been activated", self.device.name())
                return True
            except KeyboardInterrupt:
                raise
            except ConnectionFailed as ex_value:
                self.device = None
                self.active = False
                self.error =  ex_value
                log_exception("%s connection error: ", self.name)
            except DevFailed as ex_value:
                self.device = None
                self.error =  ex_value
                self.active = False
                if 'DeviceNotDefined' in ex_value.args[0].reason:
                    self.logger.error('Device %s is not defined in DB', self.name)
                else:
                    log_exception("Activation error for %s", self.name)
                    self.reactivate = False
                    self.logger.error('Dumper restart required to activate %s', self.name)
            except Exception as ex_value:
                self.device = None
                self.error =  ex_value
                self.active = False
                log_exception("Unexpected activation error for %s", self.name)
                self.reactivate = False
                self.logger.error('Dumper restart required to activate %s', self.name)
        return False

