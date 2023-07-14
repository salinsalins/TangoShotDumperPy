from tango import AttrDataFormat

from PrototypeDumperDevice import *


class TangoAttributeNew(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder='', force=True, **kwargs):
        self.attribute_name = attribute_name
        super().__init__(device_name, **kwargs)
        self.full_name = self.device_name + '/' + attribute_name
        if not folder:
            self.folder = device_name.replace('\\', '_').replace('/', '_')
        else:
            self.folder = folder
        self.force = force
        self.attr = None
        self.x_attr = None

    def activate(self):
        if self.active:
            return True
        if not super().activate():
            self.active = False
            return False
        if self.device is None:
            self.active = False
            return self.active
        try:
            self.config = self.device.get_attribute_config_ex(self.attribute_name)
            # self.device.read_attribute(self.attribute_name)
            if self.attribute_name not in self.device.get_attribute_list():
                self.logger.error(f'{self.device_name} do not have attribute {self.attribute_name}')
                self.active = False
                self.reactivate = False
                return False
            self.active = True
            self.logger.debug("%s has been activated", self.full_name)
            return True
        except KeyboardInterrupt:
            raise
        except:
            self.active = False
            log_exception(self.logger, f'{self.device_name} Error activating attribute {self.attribute_name}')
            return False

    def read_properties(self, force=False):
        # returns dictionary with attribute properties
        if len(self.properties) == 0 and not force:
            return self.properties
        try:
            db = self.device.get_device_db()
            self.properties.update(
                db.get_device_attribute_property(self.device.device_name(), self.device_name)[self.device_name])
        except KeyboardInterrupt:
            raise
        except:
            self.properties = {}
        return self.properties

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        # save_data and save_log flags
        self.read_properties(True)
        self.read_attribute()
        self.save_properties(zip_file, folder)
        # if self.channel.y is None:
        #     print('    ', self.channel.file_name, '---- No data')
        #     return
        # addition = {}
        # if self.channel.y_attr.data_format == tango._tango.AttrDataFormat.SCALAR:
        #     # self.logger.debug("SCALAR attribute %s" % self.attribute_name)
        #     if self.properties.get("history", [False])[0] != 'True':
        #         addition = {'mark': self.channel.y}
        self.save_log(log_file)
        # self.save_data(zip_file, folder)

    def read_attribute(self):
        self.attr = self.device.read_attribute(self.attribute_name)
        self.properties['data_format'] = [str(self.attr.data_format)]
        self.properties['time'] = [str(self.attr.get_date().totime())]
        if self.attr.data_format == AttrDataFormat.SPECTRUM:
            x_name = self.attribute_name.replace('chany', 'chanx')
            if x_name == self.attribute_name:
                self.x_attr = None
                return
            try:
                self.x_attr = self.device.read_attribute(x_name)
            except:
                self.x_attr = None
        elif self.attr.data_format == AttrDataFormat.IMAGE:
            self.x_attr = None
            return


    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + "param" + self.attribute_name + ".txt"
        buf = "Signal_Name=%s/%s\r\n" % (self.device.name(), self.device_name)
        for prop in self.properties:
            buf += '%s=%s\r\n' % (prop, self.properties[prop][0])
        zip_file.writestr(zip_entry, buf)
        self.logger.debug('%s Properties saved to %s', self.attribute_name, zip_entry)
        return True

    def save_log(self, log_file: IO, additional_marks=None):
        if additional_marks is None:
            additional_marks = {}
        # Signal label = default mark device_name
        label = self.properties.get('label', [''])[0]
        if '' == label:
            label = self.properties.get('name', [''])[0]
        if '' == label:
            label = self.full_name
        # Units
        unit = self.properties.get('unit', [''])[0]
        # coefficient for conversion to units
        try:
            coeff = float(self.properties.get('display_unit', ['1.0'])[0])
        except:
            coeff = 1.0
        # output data format
        frmt = self.properties.get('format', ['%6.2f'])[0]
        data_format = self.properties.get('data_format', '')
        out_str = ''
        if data_format == 'SCALAR':
            out_str = f'; {label} = {frmt % self.attr.value}'
            if unit != '' and unit != 'None' and unit != 'none':
                out_str += (" %s" % unit)
        elif data_format == 'SPECTRUM':
            self.logger.info('Data save is not implemented for SPECTRUM attributes')
            if self.x_attr:
                self.compute_marks()
        elif data_format == 'IMAGE':
            self.logger.info('Data save is not implemented for IMAGE attributes')
        print(out_str[1:])
        log_file.write(out_str)
        self.logger.debug('%s Log Saved', self.full_name)
        return
        #
        #
        #
        #
        # # process marks
        # marks = self.mark_values()
        # # Find zero value
        # zero = marks.get('zero', 0.0)
        # # add additional marks
        # for mark in additional_marks:
        #     marks[mark] = additional_marks[mark]
        # # Convert all marks to mark_value = (mark - zero)*coeff
        # scaled_marks = {}
        # for mark in marks:
        #     # If it is not zero mark
        #     if not "zero" == mark:
        #         mark_name = mark
        #         # Default mark renamed to label
        #         if mark_name == "mark":
        #             mark_name = label
        #         scaled_marks[mark_name] = (marks[mark] - zero) * coeff
        # # print and save scaled_marks to log file
        # np = 0
        # for mark in scaled_marks:
        #     print("    ", end='')
        #     # printed mark device_name
        #     pmn = mark
        #     mark_value = scaled_marks[mark]
        #     # if len(mark) > 14:
        #     #     pmn = mark[:5] + '...' + mark[-6:]
        #     # print mark value
        #     if abs(mark_value) >= 1000.0:
        #         print("%14s = %7.0f %s\r\n" % (pmn, mark_value, unit), end='')
        #     elif abs(mark_value) >= 100.0:
        #         print("%14s = %7.1f %s\r\n" % (pmn, mark_value, unit), end='')
        #     elif abs(mark_value) >= 10.0:
        #         print("%14s = %7.2f %s\r\n" % (pmn, mark_value, unit), end='')
        #     else:
        #         print("%14s = %7.3f %s\r\n" % (pmn, mark_value, unit), end='')
        #     out_str = ("; %s = " % mark) + (format % mark_value)
        #     if unit != '' and unit != 'None' and unit != 'none':
        #         out_str += (" %s" % unit)
        #     log_file.write(out_str)
        #     np += 1
        # if np == 0:
        #     print('    ', label, '---- no marks')
        # self.logger.debug('%s Log Saved', self.file_name)
        #

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        t0 = time.time()
        if self.y is None:
            self.logger.debug('%s No data to save', self.file_name)
            return
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.file_name + ".txt"
        try:
            avg = int(self.read_properties().get("save_avg", ['1'])[0])
        except:
            avg = 1
        save_as_numpy = self.properties.get('save_as_numpy',['0'])[0] in PrototypeDumperDevice.TRUE_VALUES
        outbuf = ''
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
            # buf = io.BytesIO()
            # numpy.save(buf, self.y)
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
        zip_file.writestr(zip_entry, outbuf)
        # zip_file.writestr(zip_entry.replace('.txt', '.npy'), z.tobytes())
        self.logger.debug('%s Data saved to %s, total %ss', self.file_name, zip_entry, time.time() - t0)

    def compute_marks(self):
        result = {}
        for p_key in self.properties:
            if p_key.endswith("_start"):
                try:
                    pv = float(self.properties[p_key][0])
                    pln = p_key.replace("_start", "_length")
                    pl = float(self.properties[pln][0])
                    mark_name = p_key.replace("_start", "")
                    if pl > 0.0:
                        result[mark_name] = (pv, pv + pl)
                except:
                    pass
        # self.marks = result
        mrk = result
        for key in mrk:
            try:
                rng = mrk[key]
                # index = numpy.logical_and(self.x >= rng[0], self.x <= rng[1])
                # if numpy.any(index):
                #     result[key] = self.y[index].mean()
                # else:
                #     result[key] = float('nan')
                index = numpy.searchsorted(self.x_attr.value, [rng[0], rng[1]])
                result[key] = self.attr.value[index[0]:index[1]].mean()
            except:
                result[key] = float('nan')
        self.marks = result
        return result
