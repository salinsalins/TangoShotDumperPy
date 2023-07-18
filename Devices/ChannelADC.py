from tango import AttrDataFormat
from Devices.TangoAttributeNew import *


class ChannelADC(TangoAttributeNew):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_attr = None

    def read_attribute(self):
        super().read_attribute()
        if self.attr.data_format != AttrDataFormat.SPECTRUM:
            self.logger.info('Channel must be SPECTRUM')
            self.active = False
            self.reactivate = False
            return
        x_name = self.attribute_name.replace('chany', 'chanx')
        if x_name == self.attribute_name:
            self.x_attr = None
            return
        try:
            self.x_attr = self.device.read_attribute(x_name)
        except KeyboardInterrupt:
            raise
        except:
            self.x_attr = None
        return

    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        flag1 = self.as_boolean(self.read_properties().get("save_data", ['0'])[0])
        flag2 = self.as_boolean(self.read_properties().get("save_log", ['0'])[0])
        if not (flag1 and flag2):
            self.logger.debug('%s save_properties not allowed', self.full_name)
            return False
        return super().save_properties(zip_file, folder)

    def save_log(self, log_file: IO, additional_marks=None):
        flag = self.as_boolean(self.read_properties().get("save_log", ['0'])[0])
        if not flag:
            self.logger.debug('%s save_log not allowed', self.full_name)
            return False
        return super().save_log(log_file, additional_marks)

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        flag = self.as_boolean(self.read_properties().get("save_data", ['0'])[0])
        if not flag:
            self.logger.debug('%s save_data not allowed', self.full_name)
            return False
        t0 = time.time()
        if self.attr is None:
            self.logger.debug('%s No data to save', self.full_name)
            return False
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.attribute_name + ".txt"
        avg = self.as_int(self.read_properties().get("save_avg", ['1'])[0], 1)
        data_format = self.properties.get('data_format', '')[0]
        if data_format != 'SPECTRUM':
            self.logger.info('Channel must be SPECTRUM, data not saved')
            self.active = False
            self.reactivate = False
            return False
        y = self.smooth(self.attr.value, avg)
        if not hasattr(self, 'x_attr') or self.x_attr is None:
            self.attr.value = y
            return super().save_data(zip_file, folder)
        x = self.smooth(self.x_attr.value, avg)
        # save "x; y" pairs
        fmt = '%f; %f'
        fmtcrlf = fmt + '\r\n'
        n = min(len(x), len(y))
        # r = int(n % avg)
        # d = int(n / avg)
        # avg = int(avg)
        # ynps = self.y[:n-r].reshape((d, avg)).mean(1)
        # xnps = self.x[:n-r].reshape((d, avg)).mean(1)
        # z = numpy.vstack((xnps, ynps)).T
        # buf = io.BytesIO()
        # numpy.save(buf, self.y)
        xs = 0.0
        ys = 0.0
        ns = 0.0
        outbuf = ''
        for k in range(n - 2):
            xs += x[k]
            ys += y[k]
            ns += 1.0
            if ns >= avg:
                s = fmtcrlf % (xs / ns, ys / ns)
                outbuf += s.replace(",", ".")
                xs = 0.0
                ys = 0.0
                ns = 0.0
        xs += x[n - 1]
        ys += y[n - 1]
        ns += 1.0
        s = fmt % (xs / ns, ys / ns)
        outbuf += s.replace(",", ".")
        zip_file.writestr(zip_entry, outbuf)
        self.logger.debug('%s Data saved to %s, total %ss', self.full_name, zip_entry, time.time() - t0)
