import io
import json

from PrototypeDumperDeviceNew import *


class TangoAttributeNew(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder=None, force=True, **kwargs):
        super().__init__(device_name, **kwargs)
        self.attribute_name = attribute_name
        self.full_name = self.device_name + '/' + attribute_name
        if folder is None:
            # self.folder = device_name.replace('\\', '_').replace('/', '_')
            self.folder = device_name
        else:
            self.folder = folder
        self.force = force
        self.config = None
        self.attr = None
        self.marks = json.loads(kwargs.get('marks', '{}'))

    def activate(self):
        if self.active:
            return True
        if not super().activate():
            self.active = False
            return False
        if self.device is None:
            self.active = False
            return False
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

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        if not self.read_properties(True):
            return False
        properties_saved = self.save_properties(zip_file, folder)
        data_ready = self.read_attribute()
        if not data_ready:
            return False
        log_saved = self.save_log(log_file)
        data_saved = self.save_data(zip_file, folder)
        if log_saved and data_saved and properties_saved:
            return True
        self.logger.warning("Error saving %s" % self.full_name)
        return False

    def read_properties(self, force=False):
        # returns dictionary with attribute properties
        retry_count = self.get_property("retry_count", 3)
        while retry_count > 0:
            retry_count -= 1
            try:
                self.config = self.device.get_attribute_config_ex(self.attribute_name)[0]
                al = ['dim_x', 'dim_y', 'max_dim_x', 'max_dim_y', 'data_format', 'data_type',
                      'unit', 'label', 'display_unit', 'format', 'min_value', 'max_value',
                      'name', 'is_empty', 'has_failed', 'quality', 'nb_read', 'nb_written',
                      'time']
                for a in al:
                    val = getattr(self.config, a, None)
                    if val is not None:
                        self.properties[a] = [str(val)]
                # user defined attribute properties
                db = self.device.get_device_db()
                pr = db.get_device_attribute_property(self.device_name, self.attribute_name)[self.attribute_name]
                self.properties.update(pr)
                return True
            except KeyboardInterrupt:
                raise
            except:
                if retry_count == 2:
                    log_exception(self.logger, '%s Can not read properties', self.full_name, no_info=False)
        self.logger.warning('%s Can not read properties', self.full_name)
        return False

    def read_attribute(self, **kwargs):
        retry_count = self.get_property("retry_count", 3)
        while retry_count > 0:
            retry_count -= 1
            try:
                device = kwargs.get('device', None)
                if device is None:
                    device = self.device
                attr_name = kwargs.get('attr_name', None)
                if attr_name is None:
                    attr_name = self.attribute_name
                self.attr = device.read_attribute(attr_name)
                al = ['dim_x', 'dim_y', 'max_dim_x', 'max_dim_y', 'data_format', 'data_type',
                      'unit', 'label', 'display_unit', 'format', 'min_value', 'max_value',
                      'name', 'is_empty', 'has_failed', 'quality', 'nb_read', 'nb_written',
                      'time']
                for a in al:
                    val = getattr(self.attr, a, '')
                    if val:
                        self.properties[a] = [str(val)]
                self.properties['time_s'] = [str(self.attr.get_date().totime())]
                return True
            except KeyboardInterrupt:
                raise
            except:
                if retry_count == 2:
                    log_exception("Error reading %s" % self.full_name)
        self.logger.warning('Can not read %s', self.full_name)
        return False

    def save_properties(self, zip_file, folder=''):
        if not folder.endswith('/'):
            folder += '/'
        zip_entry = folder + self.attribute_name + "_parameters.txt"
        buf = io.StringIO('')
        buf.write("Signal_Name=%s\r\n" % self.full_name)
        for prop in self.properties:
            buf.write('%s=%s\r\n' % (prop, self.properties[prop][0]))
        zip_file.writestr(zip_entry, buf.getvalue())
        self.logger.debug('%s Properties saved to %s', self.full_name, zip_entry)
        return True

    def save_log(self, log_file, additional_marks=None):
        if self.attr is None:
            return False
        if additional_marks is None:
            additional_marks = {}
        # Signal label = default mark device_name
        label = self.properties.get('label', [''])[0]
        if '' == label:
            label = self.properties.get('name', [''])[0]
        if '' == label:
            label = self.full_name
        # Units
        unit = self.get_property('unit', '')
        # coefficient for conversion to units
        coeff = self.get_property('display_unit', 1.0)
        # output data format
        frmt = self.get_property('format', '%6.2f')
        data_format = self.get_property('data_format', '')
        if data_format == 'SCALAR':
            out_str = f'; {label} = {frmt % (self.attr.value * coeff)}'
            if unit != '' and unit != 'None' and unit != 'none':
                out_str += (" %s" % unit)
            self.print_log(label, self.attr.value, unit)
            log_file.write(out_str)
        elif data_format == 'SPECTRUM':
            self.compute_marks()
            self.marks.update(additional_marks)
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
            self.logger.debug('Log save is not implemented for IMAGE attributes')
            return True
        self.logger.debug('%s Log Saved', self.full_name)
        return True

    def save_data(self, zip_file, folder=''):
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
        data_format = self.get_property('data_format', '')
        save_format = self.get_property('save_format', '%f')
        n = 1
        m = 1
        if data_format == 'SCALAR':
            zip_file.writestr(zip_entry, (save_format % self.attr.value).replace(",", "."))
        elif data_format == 'SPECTRUM':
            n = self.attr.value.shape[0]
            frmt = save_format + '\r\n'
            buf = io.StringIO('')
            try:
                for v in self.attr.value:
                    s = frmt % v
                    buf.write(s.replace(",", "."))
                zip_file.writestr(zip_entry, buf.getvalue())
            except KeyboardInterrupt:
                raise
            except:
                log_exception('%s conversion error', self.full_name)
                return False
        elif data_format == 'IMAGE':
            if len(self.attr.value.shape) < 2:
                self.logger.info('Wrong data format for IMAGE attribute %s', self.full_name)
                return False
            n = self.attr.value.shape[0]
            m = self.attr.value.shape[1]
            frmt = ((save_format + '; ') * m)[:-2] + '\r\n'
            buf = io.StringIO('')
            try:
                for i in range(n):
                    s = frmt % tuple(self.attr.value[i,:])
                    buf.write(s.replace(",", "."))
                zip_file.writestr(zip_entry, buf.getvalue())
            except KeyboardInterrupt:
                raise
            except:
                log_exception('%s conversion error', self.full_name)
                return False
        self.logger.debug('%s Data saved to %s. Total %s*%s points in % s', self.full_name, zip_entry, n, m, time.time() - t0)
        return True

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
                except KeyboardInterrupt:
                    raise
                except:
                    pass
        mrks = {}
        for key in result:
            try:
                rng = result[key]
                if hasattr(self, 'x_attr') and self.x_attr is not None:
                    index = numpy.searchsorted(self.x_attr.value, [rng[0], rng[1]])
                    if index[0] < index[1]:
                        mrks[key] = self.attr.value[index[0]:index[1]].mean()
                    else:
                        mrks[key] = self.attr.value[index[0]]
                else:
                    mrks[key] = self.attr.value[int(rng[0]):int(rng[1]+1)].mean()
                    # self.logger.debug('%s(%s:%s) = %s', key, int(rng[0]), int(rng[1]+1), mrks[key])
            except KeyboardInterrupt:
                raise
            except:
                mrks[key] = float('nan')
        self.marks.update(mrks)
        return mrks
