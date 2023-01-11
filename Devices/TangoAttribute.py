import io
import logging

from tango import AttrDataFormat

from PrototypeDumperDevice import *
from TangoDevice import TangoDevice
from TangoUtils import TangoDeviceAttributeProperties


def average_aray(arr, avg):
    if avg > 1:
        n = len(arr)
        m = n // avg
        if m > 0:
            y = arr[:(m*avg)]
            return numpy.average(y.reshape((m, avg)), 1)
        else:
            return numpy.average(arr)
    else:
        return numpy.average(arr)


class TangoAttribute():
    def __init__(self, device_name, attribute_name, folder='', use_history=False):
        self.device = TangoDevice(device_name)
        self.logger = self.device.logger
        self.active = False
        self.error = None
        self.attribute_name = attribute_name
        self.full_name = self.device.name + '/' + attribute_name
        self.folder = folder
        self.use_history = use_history
        self.attr = None
        self.value = None
        self.config = {}
        self.properties = {}

    def activate(self):
        if not self.device.activate():
            self.active = False
            self.error = self.device.error
            return False
        if self.active:
            return True
        try:
            if self.attribute_name not in self.device.device.get_attribute_list():
                msg = f'{self.device.name} do not have attribute {self.attribute_name}'
                self.logger.warning(msg)
                self.active = False
                self.error = Exception(msg)
                return False
            self.config = self.device.device.get_attribute_config_ex(self.attribute_name)[0]
            # self.logger.debug("config = %s", self.config)
            self.active = True
            self.error = None
            return True
        except KeyboardInterrupt:
            raise
        except Exception as ex_value:
            self.error =  ex_value
            self.active = False
            log_exception(f'Error activating attribute {self.attribute_name}')
            return False

    def save(self, log_file, zip_file, folder=None):
        if not self.active:
            return
        if folder is None:
            folder = self.folder
        try:
            self.properties = TangoDeviceAttributeProperties(self.device.name, self.attribute_name)()
            self.attr = self.device.device.read_attribute(self.attribute_name)
            self.value = self.attr.value
            if self.value is None:
                print('    ', self.attribute_name, ' ---- No data')
                return
            self.save_properties(zip_file, folder)
            self.save_log(log_file)
            self.save_data(zip_file, folder)
        except KeyboardInterrupt:
            raise
        except:
            print('    ', self.attribute_name, ' ---- read ERROR')
            log_exception(f'Can not read attribute {self.full_name}', level=logging.DEBUG)

    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.full_name + '_properties' + '.txt'
        buf = b"Full_Name=%s\r\n" % self.full_name
        for prop in self.properties:
            buf += b'%s=%s\r\n' % (prop, self.properties[prop][0])
        # buf += b'%s=%s\r\n' % ('data_format', self.config.data_format)
        zip_file.writestr(zip_entry, buf)
        self.logger.debug('%s properties saved to %s', self.full_name, zip_entry)
        return True

    def save_log(self, log_file: IO, additional_marks=None):
        if additional_marks is None:
            additional_marks = {}
        # label
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

    def save_data(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if self.value is None:
            self.logger.debug('%s No data to save', self.full_name)
            return
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.full_name + ".txt"
        if self.value.data_format == AttrDataFormat.SCALAR:
            pass
        elif self.value.data_format == AttrDataFormat.SPECTRUM:
            pass
        elif self.value.data_format == AttrDataFormat.IMAGE:
            pass
        else:
            self.logger.warning('Wrong data format for %s', self.full_name)
            return
        try:
            avg = int(self.properties.get("save_avg", ['1'])[0])
        except:
            avg = 1

        y = average_aray(self.value, avg)

        try:
            save_as_numpy = self.properties.get('save_as_numpy', ['0'])[0] in PrototypeDumperDevice.TRUE_VALUES
        except:
            save_as_numpy = False

        t0 = time.time()

        bio = io.BytesIO()
        numpy.savetxt(bio, y)
        # outbuf = bio.getvalue()
        outbuf = bio.getbuffer()

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


