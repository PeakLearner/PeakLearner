import os
import time
import shutil
import tarfile
import unittest
import threading

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbTar = os.path.join('data', 'db.tar.gz')
testDataPath = os.path.join('tests', 'data')

from core.util import PLConfig as cfg, PLdb as db

cfg.testing()
sleepTime = 600

lockDetect = True

def checkLocks():
    while lockDetect:
        db.deadlock_detect()
        time.sleep(1)


def lock_detect(func):
    def wrap(*args, **kwargs):
        global lockDetect
        thread = threading.Thread(target=checkLocks)
        thread.start()
        out = func(*args, **kwargs)
        lockDetect = False
        thread.join(timeout=5)
        return out

    return wrap


class PeakLearnerTestBase(unittest.TestCase):

    def setUp(self):
        if db.isLoaded():
            db.closeDBs()

        if os.path.exists(dbDir):
            shutil.rmtree(dbDir)
        with tarfile.open(dbTar) as tar:
            tar.extractall(dataDir)

        if not db.isLoaded():
            db.openDBs()
        else:
            raise Exception
