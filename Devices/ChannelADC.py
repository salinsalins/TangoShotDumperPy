from tango import AttrDataFormat
from Devices.TangoAttribute import *


class ChannelADC(TangoAttribute):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_attr = DeviceAttribute()
        self.avg = kwargs.get('avg', None)

    def read_attribute(self):
        if not super().read_attribute():
            return False
        if self.attr.data_format != AttrDataFormat.SPECTRUM:
            self.logger.info('Channel must be SPECTRUM')
            self.active = False
            self.reactivate = False
            return False
        x_name = self.attribute_name.replace('chany', 'chanx')
        if x_name == self.attribute_name:
            self.x_attr = None
            return True
        try:
            self.x_attr = self.device.read_attribute(x_name)
        except KeyboardInterrupt:
            raise
        except:
            self.x_attr = None
            return False
        return True

    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        flag1 = self.get_property("save_data", False)
        flag2 = self.get_property("save_log", False)
        if not (flag1 and flag2):
            # self.logger.debug('%s save properties not allowed', self.full_name)
            return True
        return super().save_properties(zip_file, folder)

    def save_log(self, log_file: IO, additional_marks=None):
        flag = self.get_property("save_log", False)
        if not flag:
            # self.logger.debug('%s save log not allowed', self.full_name)
            return True
        return super().save_log(log_file, additional_marks)

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        flag = self.get_property("save_data", False)
        if not flag:
            # self.logger.debug('%s save data not allowed', self.full_name)
            return True
        t0 = time.time()
        if self.attr is None:
            self.logger.debug('%s No data to save', self.full_name)
            return False
        if self.attr.value is None:
            self.logger.debug('%s Empty attribute - no data to save', self.full_name)
            return True
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.attribute_name + ".txt"
        if self.avg is None:
            avg = self.get_property("save_avg", 1)
        else:
            avg = self.avg
        data_format = self.get_property('data_format', '')
        n = 1
        m = len(self.attr.value)
        if data_format != 'SPECTRUM':
            self.logger.info('Channel must be SPECTRUM, data not saved')
            self.active = False
            self.reactivate = False
            return False
        y = self.smooth(self.attr.value, avg)
        if (not hasattr(self, 'x_attr')) or self.x_attr is None:
            old_value = self.attr.value
            self.attr.value = y
            n = len(y)
            result = super().save_data(zip_file, folder)
            self.attr.value = old_value
        else:
            x = self.smooth(self.x_attr.value, avg)
            n = min(len(x), len(y))
            old_value = self.attr.value
            self.attr.value = numpy.stack((x[:n], y[:n]), 1)
            old_data_format = self.properties['data_format']
            self.properties['data_format'] = ['IMAGE']
            result = super().save_data(zip_file, folder)
            self.attr.value = old_value
            self.properties['data_format'] = old_data_format
        if result:
            self.logger.debug('%s Data saved to %s. Total %s points of %s averaged by %s in %s s', self.full_name, zip_entry, n, m, avg, time.time() - t0)
            # self.logger.debug('%s Data saved to %s, total %ss', self.full_name, zip_entry, time.time() - t0)
        else:
            self.logger.debug('%s Data saved to %s with errors, total %s s', self.full_name, zip_entry, time.time() - t0)
        return result

