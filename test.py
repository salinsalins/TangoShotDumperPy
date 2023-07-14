import sys
import time
import traceback
from queue import Queue
from socket import socket, AF_INET, SOCK_STREAM

import select
from tango import DevFailed, ConnectionFailed


class Task(object):
    taskid = 0

    def __init__(self, target):
        Task.taskid += 1
        self.tid = Task.taskid  # Task ID
        self.target = target  # Target coroutine
        self.sendval = None  # Value to send

    def run(self):
        return self.target.send(self.sendval)


class Scheduler(object):
    def __init__(self):
        self.ready = Queue()
        self.taskmap = {}
        self.exit_waiting = {}
        self.read_waiting = {}
        self.write_waiting = {}

    def new(self, target):
        newtask = Task(target)
        self.taskmap[newtask.tid] = newtask
        self.schedule(newtask)
        return newtask.tid

    def schedule(self, task):
        self.ready.put(task)

    def exit(self, task):
        print("Task %d terminated" % task.tid)
        del self.taskmap[task.tid]
        # Notify other tasks waiting for exit
        for task in self.exit_waiting.pop(task.tid, []):
            self.schedule(task)

    def waitforexit(self, task, waittid):
        if waittid in self.taskmap:
            self.exit_waiting.setdefault(waittid, []).append(task)
            return True
        else:
            return False

    def mainloop(self):
        self.new(self.iotask())  # Launch I/O polls
        while self.taskmap:
            task = self.ready.get()
            try:
                result = task.run()
                if isinstance(result, SystemCall):
                    result.task = task
                    result.sched = self
                    result.handle()
                    continue
            except StopIteration:
                self.exit(task)
                continue
            self.schedule(task)

    def waitforread(self, task, fd):
        self.read_waiting[fd] = task

    def waitforwrite(self, task, fd):
        self.write_waiting[fd] = task

    def iopoll(self, timeout):
        if self.read_waiting or self.write_waiting:
            r, w, e = select.select(self.read_waiting, self.write_waiting, [], timeout)
            for fd in r: self.schedule(self.read_waiting.pop(fd))
            for fd in w: self.schedule(self.write_waiting.pop(fd))

    def iotask(self):
        while True:
            if self.ready.empty():
                self.iopoll(None)
            else:
                self.iopoll(0)
            yield


class SystemCall(object):
    def __init__(self):
        self.task = None
        self.sched = None

    def handle(self):
        raise NotImplemented


class GetTid(SystemCall):
    def handle(self):
        self.task.sendval = self.task.tid
        self.sched.schedule(self.task)


class NewTask(SystemCall):
    def __init__(self, target):
        super().__init__()
        self.target = target

    def handle(self):
        tid = self.sched.new(self.target)
        self.task.sendval = tid
        self.sched.schedule(self.task)


class KillTask(SystemCall):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    def handle(self):
        task = self.sched.taskmap.get(self.tid, None)
        if task:
            task.target.close()
            self.task.sendval = True
        else:
            self.task.sendval = False
        self.sched.schedule(self.task)


class WaitTask(SystemCall):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    def handle(self):
        result = self.sched.waitforexit(self.task, self.tid)
        self.task.sendval = result
        # If waiting for a non-existent task,
        # return immediately without waiting
        if not result:
            self.sched.schedule(self.task)


class ReadWait(SystemCall):
    def __init__(self, f):
        super().__init__()
        self.f = f

    def handle(self):
        fd = self.f.fileno()
        self.sched.waitforread(self.task, fd)


class WriteWait(SystemCall):
    def __init__(self, f):
        super().__init__()
        self.f = f

    def handle(self):
        fd = self.f.fileno()
        self.sched.waitforwrite(self.task, fd)


def foo():
    mytid = yield GetTid()
    while True:
        print("I'm foo", mytid)
        yield


def bar():
    mytid = yield GetTid()
    for i in range(5):
        print("I'm bar", mytid)
        yield


def main():
    child = yield NewTask(bar())
    print("Waiting for child")
    yield WaitTask(child)
    print("main done")


def handle_client(client, addr):
    print("Connection from", addr)
    while True:
        yield ReadWait(client)
        data = client.recv(65536)
        if not data:
            break
        yield WriteWait(client)
        client.send(data)
    client.close()
    print("Client closed")


def server(port):
    print("Server starting")
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(("", port))
    sock.listen(5)
    while True:
        yield ReadWait(sock)
        client, addr = sock.accept()
        yield NewTask(handle_client(client, addr))


def alive():
    while True:
        print("I'm alive!")
        yield


sched = Scheduler()
sched.new(alive())
sched.new(server(45000))
sched.mainloop()


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
# device_name = 'sys/tg_test/1'
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
    print('total', time.time() - t00, '  max', dtmax, '  min', dtmin, '  avg', dt / n)
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
