from tango import AttrDataFormat

from PrototypeDumperDeviceNew import *


class TangoAttributeNew(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder='', force=True, **kwargs):
        super().__init__(device_name, **kwargs)
        self.attribute_name = attribute_name
        self.full_name = self.device_name + '/' + attribute_name
        if not folder:
            self.folder = device_name.replace('\\', '_').replace('/', '_')
        else:
            self.folder = folder
        self.force = force
        self.config = None
        self.attr = None
        self.marks = {}

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
            log_exception(self.logger, f'{self.device_name} Error activating {self.attribute_name}')
            return False

    def read_properties(self, force=False):
        # returns dictionary with attribute properties
        if len(self.properties) > 0 and not force:
            return self.properties
        try:
            self.config = self.device.get_attribute_config_ex(self.attribute_name)[0]
            al = ['max_dim_x', 'max_dim_x', 'data_format', 'data_type', 'unit', 'label', 'display_unit',
                  'format', 'min_value', 'max_value', 'name']
            for a in al:
                val = getattr(self.config, a)
                self.properties[a] = [str(val)]
            db = self.device.get_device_db()
            self.properties.update(
                db.get_device_attribute_property(self.device_name, self.attribute_name)[self.attribute_name])
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
        self.save_log(log_file)
        self.save_data(zip_file, folder)

    def read_attribute(self):
        self.attr = self.device.read_attribute(self.attribute_name)
        self.properties['data_format'] = [str(self.attr.data_format)]
        self.properties['time'] = [str(self.attr.get_date().totime())]
        return

    def save_properties(self, zip_file: zipfile.ZipFile, folder: str = ''):
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + "param" + self.attribute_name + ".txt"
        buf = "Signal_Name=%s\r\n" % self.full_name
        for prop in self.properties:
            buf += '%s=%s\r\n' % (prop, self.properties[prop][0])
        zip_file.writestr(zip_entry, buf)
        self.logger.debug('%s Properties saved to %s', self.full_name, zip_entry)
        return True

    def save_log(self, log_file: IO, additional_marks=None):
        if self.attr is None:
            return
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
        data_format = self.properties.get('data_format', [''])[0]
        if data_format == 'SCALAR':
            out_str = f'; {label} = {frmt % self.attr.value}'
            if unit != '' and unit != 'None' and unit != 'none':
                out_str += (" %s" % unit)
            self.print_log(label, self.attr.value, unit)
            log_file.write(out_str)
        elif data_format == 'SPECTRUM':
            self.compute_marks()
            zero = self.marks.get('zero', 0.0)
            np = 0
            for mark in self.marks:
                # If it is not zero mark
                if not "zero" == mark:
                    mark_name = mark
                    # Default mark renamed to label
                    if mark_name == "mark":
                        mark_name = label
                    mark_value = (self.marks[mark] - zero) * coeff
                    self.print_log(mark_name, mark_value, unit)
                    out_str = ("; %s = " % mark_name) + (frmt % mark_value)
                    if unit != '' and unit != 'None' and unit != 'none':
                        out_str += (" %s" % unit)
                    log_file.write(out_str)
                    np += 1
            if np == 0:
                print('    ', label, '---- no marks')
        elif data_format == 'IMAGE':
            self.logger.info('Log save is not implemented for IMAGE attributes')
            return
        self.logger.debug('%s Log Saved', self.full_name)
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
        if data_format == 'SCALAR':
            zip_file.writestr(zip_entry, ('%f' % self.attr.value).replace(",", "."))
        elif data_format == 'SPECTRUM':
            fmtcrlf = '%f' + '\r\n'
            try:
                for v in self.attr.value:
                    s = fmtcrlf % v
                    zip_file.writestr(zip_entry, s.replace(",", "."))
            except KeyboardInterrupt:
                raise
            except:
                pass
        elif data_format == 'IMAGE':
            self.logger.info('Data save is not implemented for IMAGE attributes')
            return
        self.logger.debug('%s Data saved to %s, total %ss', self.full_name, zip_entry, time.time() - t0)

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
        mrks = {}
        for key in result:
            try:
                rng = result[key]
                # index = numpy.logical_and(self.x >= rng[0], self.x <= rng[1])
                # if numpy.any(index):
                #     result[key] = self.y[index].mean()
                # else:
                #     result[key] = float('nan')
                if hasattr(self, 'x_attr') and self.x_attr is not None:
                    index = numpy.searchsorted(self.x_attr.value, [rng[0], rng[1]])
                    mrks[key] = self.attr.value[index[0]:index[1]].mean()
                else:
                    mrks[key] = self.attr.value[int(rng[0]):int(rng[1])].mean()
            except:
                mrks[key] = float('nan')
        self.marks = mrks
        return mrks
