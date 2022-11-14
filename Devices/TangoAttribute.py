from PrototypeDumperDevice import *


class TangoAttribute(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder=None, force=True, **kwargs):
        self.attribute_name = attribute_name
        super().__init__(device_name, **kwargs)
        self.folder = folder
        self.force = force
        self.channel = PrototypeDumperDevice.Channel(self.device, attribute_name)
        self.channel.logger = self.logger
        self.full_name = self.name + '/' + attribute_name

    def activate(self):
        super().activate()
        if self.device is None:
            self.active = False
            return self.active
        try:
            self.channel.device = self.device
            self.device.read_attribute(self.attribute_name)
            # if self.active and self.attribute_name not in self.device.get_attribute_list():
            #     self.logger.error(f'{self.name} do not have attribute {self.attribute_name}')
            #     self.active = False
            #     return False
            self.active = True
            return self.active
        except:
            self.logger.error(f'{self.name} do not have attribute {self.attribute_name}')
            self.active = False
            log_exception('Error reading attribute')
            return self.active

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        # save_data and save_log flags
        properties = self.channel.read_properties(True)
        self.read_attribute()
        self.channel.save_properties(zip_file, folder)
        if self.channel.y is None:
            print('    ', self.channel.file_name, '---- No data')
            return
        addition = {}
        if self.channel.y_attr.data_format == tango._tango.AttrDataFormat.SCALAR:
            # self.logger.debug("SCALAR attribute %s" % self.attribute_name)
            if properties.get("history", [False])[0] != 'True':
                addition = {'mark': self.channel.y}
        self.channel.save_log(log_file, addition)
        self.channel.save_data(zip_file, folder)

    def read_attribute(self):
        self.channel.read_y()
        if self.channel.y_attr.data_format == tango._tango.AttrDataFormat.IMAGE:
            self.channel.x = self.channel.y_attr.value[:, 0]
            self.channel.y = self.channel.y_attr.value[:, 1]
        elif self.channel.y_attr.data_format != tango._tango.AttrDataFormat.SCALAR:
            self.channel.read_x()


