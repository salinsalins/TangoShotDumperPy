from tango import AttrDataFormat

from PrototypeDumperDevice import *


class TangoAttribute(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder=None, force=True, **kwargs):
        super().__init__(device_name, **kwargs)
        self.attribute_name = attribute_name
        self.folder = folder
        self.force = force
        # self.channel = PrototypeDumperDevice.Channel(self.device, attribute_name)
        # self.channel.logger = self.logger
        self.full_name = self.device_name + '/' + attribute_name
        self.value = None
        self.config = {}
        self.properties = {}

    def activate(self):
        if self.active:
            return self.active
        if not super().activate():
            self.active = False
            return False
        try:
            #self.device.read_attribute(self.attribute_name)
            if self.attribute_name not in self.device.get_attribute_list():
                self.logger.error(f'{self.device_name} do not have attribute {self.attribute_name}')
                self.active = False
                return False
            self.config = self.device.get_attribute_config_ex(self.attribute_name)
            # self.logger.debug("config = %s", self.config)
            self.active = True
            return True
        except:
            self.active = False
            log_exception('Error reading attribute')
            return False

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        db = tango.Database()
        self.properties = db.get_device_attribute_property(self.device_name, self.attribute_name)[self.attribute_name]
        self.save_properties(zip_file, folder)
        self.value = self.device.read_attribute(self.attribute_name)
        if self.channel.y is None:
            print('    ', self.channel.file_name, '---- No data')
            return
        addition = {}
        if self.channel.y_attr.data_format == AttrDataFormat.SCALAR:
            # self.logger.debug("SCALAR attribute %s" % self.attribute_name)
            if properties.get("history", [False])[0] != 'True':
                addition = {'mark': self.channel.y}
        self.channel.save_log(log_file, addition)
        self.channel.save_data(zip_file, folder)

    def save_log(self, log_file: IO, additional_marks=None):
        if additional_marks is None:
            additional_marks = {}
        self.read_properties()
        # Signal label = default mark name
        label = self.properties.get('label', [''])[0]
        if '' == label:
            label = self.properties.get('name', [''])[0]
        if '' == label:
            label = self.file_name
        # Units
        unit = self.properties.get('unit', [''])[0]
        # coefficient for conversion to units
        try:
            coeff = float(self.properties.get('display_unit', ['1.0'])[0])
        except:
            coeff = 1.0
        # output data format
        format = self.properties.get('format', ['%6.2f'])[0]
        # process marks
        marks = self.mark_values()
        # Find zero value
        zero = marks.get('zero', 0.0)
        # add additional marks
        for mark in additional_marks:
            marks[mark] = additional_marks[mark]
        # Convert all marks to mark_value = (mark - zero)*coeff
        scaled_marks = {}
        for mark in marks:
            # If it is not zero mark
            if not "zero" == mark:
                mark_name = mark
                # Default mark renamed to label
                if mark_name == "mark":
                    mark_name = label
                scaled_marks[mark_name] = (marks[mark] - zero) * coeff
        # print and save scaled_marks to log file
        np = 0
        for mark in scaled_marks:
            print("    ", end='')
            # printed mark name
            pmn = mark
            mark_value = scaled_marks[mark]
            # if len(mark) > 14:
            #     pmn = mark[:5] + '...' + mark[-6:]
            # print mark value
            if abs(mark_value) >= 1000.0:
                print("%14s = %7.0f %s\r\n" % (pmn, mark_value, unit), end='')
            elif abs(mark_value) >= 100.0:
                print("%14s = %7.1f %s\r\n" % (pmn, mark_value, unit), end='')
            elif abs(mark_value) >= 10.0:
                print("%14s = %7.2f %s\r\n" % (pmn, mark_value, unit), end='')
            else:
                print("%14s = %7.3f %s\r\n" % (pmn, mark_value, unit), end='')
            out_str = ("; %s = " % mark) + (format % mark_value)
            if unit != '':
                out_str += (" %s" % unit)
            log_file.write(out_str)
            np += 1
        if np == 0:
            print('    ', label, '---- no marks')
        self.logger.debug('%s Log Saved', self.file_name)

    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.full_name + '_properties' + '.txt'
        buf = "Attribute_Name=%s/\r\n" % self.full_name
        for prop in self.properties:
            buf += '%s=%s\r\n' % (prop, self.properties[prop][0])
        zip_file.writestr(zip_entry, buf)
        self.logger.debug('%s properties saved to %s', self.full_name, zip_entry)
        return True

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if self.y is None:
            self.logger.debug('%s No data to save', self.file_name)
            return
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.file_name + ".txt"
        avg = int(self.read_properties().get("save_avg", ['1'])[0])
        save_as_numpy = self.properties.get('save_as_numpy',['0'])[0] in PrototypeDumperDevice.TRUE_VALUES
        outbuf = ''
        t0 = time.time()
        if self.x is None:
            # save only y values
            fmt = '%f'
            fmtcrlf = fmt + '\r\n'
            try:
                n = len(self.y)
                ys = 0.0
                ns = 0.0
                for k in range(n - 2):
                    ys += self.y[k]
                    ns += 1.0
                    if ns >= avg:
                        s = fmtcrlf % (ys / ns)
                        outbuf += s.replace(",", ".")
                        ys = 0.0
                        ns = 0.0
                ys += self.y[n - 1]
                ns += 1.0
                s = fmt % (ys / ns)
                outbuf += s.replace(",", ".")
            except:
                s = fmt % self.y
                outbuf += s.replace(",", ".")
        else:
            # save "x; y" pairs
            fmt = '%f; %f'
            fmtcrlf = fmt + '\r\n'
            n = min(len(self.x), len(self.y))
            # r = int(n % avg)
            # d = int(n / avg)
            # avg = int(avg)
            # ynps = self.y[:n-r].reshape((d, avg)).mean(1)
            # xnps = self.x[:n-r].reshape((d, avg)).mean(1)
            # z = numpy.vstack((xnps, ynps)).T
            xs = 0.0
            ys = 0.0
            ns = 0.0
            for k in range(n - 2):
                xs += self.x[k]
                ys += self.y[k]
                ns += 1.0
                if ns >= avg:
                    s = fmtcrlf % (xs / ns, ys / ns)
                    outbuf += s.replace(",", ".")
                    xs = 0.0
                    ys = 0.0
                    ns = 0.0
            xs += self.x[n - 1]
            ys += self.y[n - 1]
            ns += 1.0
            s = fmt % (xs / ns, ys / ns)
            outbuf += s.replace(",", ".")
        # self.logger.debug('dT = %s', time.time() - t0)
        zip_file.writestr(zip_entry, outbuf)
        # self.logger.debug('dT = %s', time.time() - t0)
        # zip_file.writestr(zip_entry.replace('.txt', '.npy'), z.tobytes())
        # self.logger.debug('dT = %s', time.time() - t0)
        self.logger.debug('%s Data saved to %s', self.file_name, zip_entry)


