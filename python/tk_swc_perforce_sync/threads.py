import threading
from sgtk.platform.qt import QtCore

#from QtCore import QRunnable, QThreadPool, pyqtSignal
from time import sleep
import sgtk
logger = sgtk.platform.get_logger(__name__)

# This class is used to sync a file in a separate thread

class SyncThread(threading.Thread):
    def __init__(self, p4=None, file_name=None):
        super().__init__()
        # Store constructor arguments (re-used for processing)
        self.p4 = p4
        self.file_name = file_name

    def sync_file(self):
        # Perform the sync operation here
        # store the result (of the sync operation) somewhere
        logger.debug("--------->>>>>>  Syncing file: {}".format(file_name))
        p4_result = self.p4.run("sync", "-f", self.file_name + "#head")
        logger.debug("--------->>>>>>  Syncing result: {}".format(p4_result))
        #sleep(0.1)

    def run(self):
        self.sync_file()


class FileSyncThread(threading.Thread):
    def __init__(self, p4=None, file_queue=None):
        super().__init__()
        self.p4 = p4
        self.file_queue = file_queue

    def run(self):
        while not self.file_queue.empty():

            file_path = self.file_queue.get()
            self.sync_file(file_path)
            #self.file_queue.task_done()
            #except queue.Empty:
            #    break

    def sync_file(self, file_path):
        # Perform the sync operation here
        # store the result (of the sync operation) somewhere
        logger.debug("--------->>>>>>  Syncing file: {}".format(file_name))
        p4_result = self.p4.run("sync", "-f", file_path + "#head")
        logger.debug("--------->>>>>>  Syncing result: {}".format(p4_result))
        # sleep(0.1)

"""
# This class is used to sync a file in a separate thread
class SyncRunnable(QtCore.QRunnable):
    sync_progress = QtCore.pyqtSignal(int)

    def __init__(self, p4=None, file_name=None):
        super().__init__()
        self.p4 = p4
        self.file_path = file_name

    def run(self):
        # Simulating the sync process
        logger.debug("--------->>>>>>  Syncing file: {}".format(file_name))
        p4_result = self.p4.run("sync", "-f", self.file_name + "#head")
        logger.debug("--------->>>>>>  Syncing result: {}".format(p4_result))

        #for progress in range(0, 101, 10):
        #    self.sync_progress.emit(progress)  # Update QProgressBar
        #    time.sleep(1)
"""


