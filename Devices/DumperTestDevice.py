import time
import numpy

from PrototypeDumperDevice import *


class DumperTestDevice(PrototypeDumperDevice):
    n = 0

    def __init__(self, delta_t=-1.0, points=0, folder='', properties=None):
        super().__init__('test_device')
        self.n = DumperTestDevice.n
        self.device_name = 'TestDevice_%d' % self.n
        self.shot = 0
        self.delta_t = delta_t
        self.points = points
        if not folder:
            self.folder = self.device_name
        else:
            self.folder = folder
        if properties is None:
            self.properties = {'device_name': ['test_device_%d' % self.n], 'label': ['Point number'], 'unit': ['a.u.']}
        else:
            self.properties = properties
        DumperTestDevice.n += 1

    def __str__(self):
        return self.device_name

    def activate(self):
        if self.active:
            return True
        self.active = True
        self.time = time.time()
        self.logger.debug("TestDevice %s activated" % self.device_name)
        return True

    def new_shot(self):
        if 0.0 < self.delta_t < (time.time() - self.time):
            self.shot += 1
            self.time = time.time()
            self.logger.debug("New shot %d from %s" % (self.shot, self.device_name))
            return True
        return False

    def save(self, log_file, zip_file, folder: str = None):
        if folder is None:
            folder = self.folder
        log_file.write('; %s=%f' % (self.device_name, self.time))
        print('     %s = %f' % (self.device_name, self.time))
        if self.points > 0:
            signal = self.Channel(None, self.n, prefix='test_device_chany')  # PrototypeDumperDevice.Channel()
            signal.x = numpy.linspace(0.0, 2.0 * numpy.pi, self.points)
            signal.y = numpy.sin(signal.x + time.time() + self.n)
            signal.save_data(zip_file, folder)
            entry = folder + '/' + signal.name.replace('chan', 'paramchan') + ".txt"
            zip_file.writestr(entry, "device_name=%s\r\nxlabel=Phase [radians]\r\nunit=a.u." % self.device_name)
