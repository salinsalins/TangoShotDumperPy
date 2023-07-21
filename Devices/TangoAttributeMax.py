import numpy

from Devices.TangoAttributeHistory import TangoAttributeHistory
from Devices.TangoAttributeNew import TangoAttributeNew


class TangoAttributeMax(TangoAttributeHistory):
    def __init__(self, device_name, attribute_name, folder=None, delta_t=120.0, **kwargs):
        super().__init__(device_name, attribute_name, folder, True, **kwargs)
        self.full_name = self.full_name.replace('_history', '_max')

    def read_attribute(self):
        super().read_attribute()
        self.properties['history'] = ['False']
        self.properties['integral'] = ['True']
        self.properties['delta_t'] = ['0.0']
        if self.y is not None:
            self.y = numpy.max(self.y)
            self.properties['delta_t'] = [str(numpy.ptp(self.x))]
            self.x = None
            return True
        return False

    def save_data(self, zip_file, folder=''):
        old_name = self.attribute_name
        self.attribute_name += '_max'
        old_value = self.attr.value
        self.attr.value = self.y
        result = TangoAttributeNew.save_data(self, zip_file, folder)
        self.attr.value = old_value
        self.attribute_name = old_name
        return result

    def save_log(self, log_file, additional_marks=None):
        old_name = self.attribute_name
        self.attribute_name += '_max'
        old_value = self.attr.value
        self.attr.value = self.y
        old_label = self.properties.get('label', None)
        self.properties['label'] = [self.attribute_name]
        result = TangoAttributeNew.save_log(self, log_file, additional_marks)
        self.attr.value = old_value
        self.attribute_name = old_name
        if old_label is not None:
            self.properties['label'] = old_label
        else:
            self.properties.pop('label', [])
        return result

    def save_properties(self, zip_file, folder=''):
        old_name = self.attribute_name
        self.attribute_name += '_max'
        old_label = self.properties.get('label', None)
        self.properties['label'] = [self.attribute_name]
        result = TangoAttributeNew.save_properties(self, zip_file, folder)
        self.attribute_name = old_name
        if old_label is not None:
            self.properties['label'] = old_label
        else:
            self.properties.pop('label', [])
        return result
