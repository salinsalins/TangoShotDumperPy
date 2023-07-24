import io
import time
import numpy

from Devices.ChannelADC import ChannelADC
from PrototypeDumperDevice import *


class DumperTestDevice(PrototypeDumperDevice):
    n = 0

    def __init__(self, delta_t=-1.0, points=0, folder='', properties=None):
        self.n = DumperTestDevice.n
        self.device_name = 'TestDevice_%d' % self.n
        self.attribute_name = 'chany%d' % self.n
        super().__init__(self.device_name)
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
            x = numpy.linspace(0.0, 2.0 * numpy.pi, self.points)
            y = numpy.sin(x + time.time() + self.n)
            frmt = '%f; %f\r\n'
            buf = io.StringIO('')
            try:
                for i in range(self.points):
                    s = frmt % (x[i], y[i])
                    buf.write(s.replace(",", "."))
                zip_entry = folder + self.attribute_name + '.txt'
                zip_file.writestr(zip_entry, buf.getvalue())
            except KeyboardInterrupt:
                raise
            except:
                log_exception('%s conversion error', self.full_name)
                return False
            entry = folder + self.attribute_name + '_parameters.txt'
            zip_file.writestr(entry, "name=%s\r\ndevice_name=%s\r\nxlabel=Phase [radians]\r\nunit=a.u." % (self.device_name, self.device_name))
