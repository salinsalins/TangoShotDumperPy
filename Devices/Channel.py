from tango import AttrDataFormat
from TangoAttributeNew import *


class Channel(TangoAttributeNew):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_attr = None

    def read_attribute(self):
        super().read_attribute()
        if self.attr.data_format == AttrDataFormat.SPECTRUM:
            x_name = self.attribute_name.replace('chany', 'chanx')
            if x_name == self.attribute_name:
                self.x_attr = None
                return
            try:
                self.x_attr = self.device.read_attribute(x_name)
            except:
                self.x_attr = None
        return

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        t0 = time.time()
        if self.attr is None:
            self.logger.debug('%s No data to save', self.full_name)
            return
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.attribute_name + ".txt"
        try:
            avg = int(self.read_properties().get("save_avg", ['1'])[0])
        except:
            avg = 1
        data_format = self.properties.get('data_format', '')[0]
        if data_format != 'SPECTRUM':
            self.logger.info('Channel must be SPECTRUM, data not saved')
            return
        y = self.smooth(self.attr.value, avg)
        if not hasattr(self, 'x_attr') or self.x_attr is None:
            self.attr.value = y
            super().save_data(zip_file, folder)
            return
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

