import time


class DelayedDevice():
    def __init__(self, parent, delay=0.0):
        self.save_list = []
        self.parent = parent
        self.delay = delay

    def save(self, log_file, zip_file, folder=None):
        self.save_list.append((time.time(), zip_file, log_file, folder))
        return True

    def activate(self):
        if self.save_list:
            t = self.save_list[0][0]
            if time.time() - t >= self.delay:
                item = self.save_list.pop(0)
                zip = item[1]
                log = item[2]
                folder = item[3]
                # save data to file

