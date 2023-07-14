import numpy

from TangoAttributeHistory import TangoAttributeHistory


class TangoAttributeMax(TangoAttributeHistory):

    def read_attribute(self):
        super().read_attribute()
        self.channel.file_name = self.channel.name + '_max'
        self.channel.properties['history'] =['False']
        self.channel.properties['max'] = ['True']
        if self.channel.y is not None:
            index = numpy.argmax(self.channel.y)
            self.channel.y = self.channel.y[index]
            # self.channel.y_attr = self.channel.y_attr[index]
            self.channel.properties['delta_t'] = [str(numpy.ptp(self.channel.x))]
            self.channel.x = None
