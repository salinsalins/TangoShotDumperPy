import sys
import time
import traceback

from tango import DevFailed, ConnectionFailed





class A:
    def hi(self):
        print("A")


class B(A):
    def hi1(self):
        print("B")


class C(A):
    def h2i(self):
        print("C")


class D(B, C):
    def hi1(self):
        print("D")
    pass


d = D()
d.hi()

import tango
name = 'sys/test/1'
#name = 'sys/tg_test/1'
attr = 'double_scalar'

t00 = time.time()
try:
    device = tango.DeviceProxy(name)
    n = 0
    dt = 0.0
    dt0 = 0.0
    dtmax = -100.
    dtmin = 100.
    while n < 10000:
        t0 = time.time()
        av = device.read_attribute(attr)
        dt0 = time.time() - t0
        dtmax = max(dtmax, dt0)
        dtmin = min(dtmin, dt0)
        dt += dt0
        n += 1
    print('total', time.time() - t00, '  max', dtmax, '  min', dtmin, '  avg', dt/n)
    print(av)

except ConnectionFailed as ex_value:
    print('ConnectionFailed', time.time() - t00, ex_value)
    ex_type, ex_value, tb = sys.exc_info()
    print('*********************', ex_type, ex_value)
    traceback.print_tb(tb)

except DevFailed as ex_value:
    print('DevFailed', time.time() - t00, ex_value)
    ex_type, ex_value, tb = sys.exc_info()
    print('*********************', ex_type, ex_value)
    traceback.print_tb(tb)

except Exception as ex_value:
    print('Exception', time.time() - t0, ex_value)
    ex_type, ex_value, tb = sys.exc_info()
    print('*********************', ex_type, ex_value)
    traceback.print_tb(tb)

# ex_type, ex_value, tb = sys.exc_info()
# print('*********************', ex_type, ex_value)
# traceback.print_tb(tb)
