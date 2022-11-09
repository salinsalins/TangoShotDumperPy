from PrototypeDumperDevice import *


class TangoAttribute(PrototypeDumperDevice):
    def __init__(self, device_name, attribute_name, folder=None, force=True, **kwargs):
        super().__init__(device_name, **kwargs)
        self.attribute_name = attribute_name
        self.folder = folder
        self.force = force
        self.channel = PrototypeDumperDevice.Channel(self.device, attribute_name)
        self.channel.logger = self.logger
        if attribute_name not in self.device.get_attribute_list():
            self.logger.error(f'{device_name} do not have attribute {attribute_name}')
            self.reactivate_if_not_defined = False
            self.active = False
            self.defined_in_db = False

    def save(self, log_file, zip_file, folder=None):
        if folder is None:
            folder = self.folder
        # save_data and save_log flags
        properties = self.channel.read_properties(True)
        sdf = self.as_boolean(properties.get("save_data", [False])[0])
        slf = self.as_boolean(properties.get("save_log", [False])[0])
        # force save if requested during attribute creation
        if self.force:
            sdf = True
            slf = True
        if sdf or slf:
            self.read_attribute()
            self.channel.save_properties(zip_file, folder)
            if self.channel.y is None:
                print('    ', self.channel.file_name, '---- No data')
                return
        if slf:
            addition = {}
            if self.channel.y_attr.data_format == tango._tango.AttrDataFormat.SCALAR:
                # self.logger.debug("SCALAR attribute %s" % self.attribute_name)
                if properties.get("history", [False])[0] != 'True':
                    addition = {'mark': self.channel.y}
            self.channel.save_log(log_file, addition)
        if sdf:
            self.channel.save_data(zip_file, folder)

    def read_attribute(self):
        self.channel.read_y()
        if self.channel.y_attr.data_format == tango._tango.AttrDataFormat.IMAGE:
            self.channel.x = self.channel.y_attr.value[:, 0]
            self.channel.y = self.channel.y_attr.value[:, 1]
        elif self.channel.y_attr.data_format != tango._tango.AttrDataFormat.SCALAR:
            self.channel.read_x()


