import time

import numpy

from PrototypeDumperDevice import *


class DumperTestDevice(PrototypeDumperDevice):
    n = 0

    def __init__(self, delta_t=-1.0, points=0, folder='DumperTest', properties=None):
        super().__init__('test_device')
        self.n = DumperTestDevice.n
        self.device_name = 'TestDevice_%d' % self.n
        self.shot = 0
        self.delta_t = delta_t
        self.points = points
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
        print('    %s = %f' % (self.device_name, self.time))
        if self.points > 0:
            t0 = time.time()
            signal = self.Channel(None, 1)  # PrototypeDumperDevice.Channel()
            signal.name = 'test_device_%d' % self.n
            signal.x = numpy.linspace(0.0, 2.0 * numpy.pi, self.points)
            signal.y = numpy.sin(signal.x)
            # signal.properties = self.properties
            # signal.properties['save_numpy'] = ['1']
            signal.save_data(zip_file, folder)
            # self.logger.debug('dT = %s', time.time() - t0)
            # signal.save_properties(zip_file, folder)
            # signal.save_properties(zip_file, folder)
            # buf = ""
            # for k in range(self.points):
            #     w = 2.0 * numpy.pi * float(k) / (self.points -1)
            #     s = '%f; %f' % (float(k), numpy.sin(w + float(self.n)) + 0.1 * numpy.sin(4.0 * w))
            #     buf += s.replace(",", ".")
            #     if k < self.points - 1:
            #         buf += '\r\n'
            # entry = folder + "/channel_%d.txt" % self.n
            # zip_file.writestr(entry, buf)
            entry = folder + "/paramchannel_%d.txt" % self.n
            zip_file.writestr(entry, "device_name=test_device_%d\r\nxlabel=Point number\r\nunit=a.u." % self.n)
