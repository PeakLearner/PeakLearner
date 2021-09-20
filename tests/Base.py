import os
import time
import shutil
import tarfile
import aiohttp
import unittest
import threading
import asynctest

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbLogBackupDir = os.path.join(dataDir, 'db_log_backup')
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
        try:
            db.closeDBs()
        except:
            pass

        if os.path.exists(dbDir):
            shutil.rmtree(dbDir)
        if os.path.exists(dbLogBackupDir):
            shutil.rmtree(dbLogBackupDir)
        with tarfile.open(dbTar) as tar:
            tar.extractall(dataDir)

        db.openEnv()
        db.openDBs()

    def tearDown(self):
        db.closeDBs()


class PeakLearnerAsyncTestBase(asynctest.TestCase):
    async def setUp(self):
        try:
            db.closeDBs()
        except:
            pass

        if os.path.exists(dbDir):
            shutil.rmtree(dbDir)
        if os.path.exists(dbLogBackupDir):
            shutil.rmtree(dbLogBackupDir)
        with tarfile.open(dbTar) as tar:
            tar.extractall(dataDir)

        db.openEnv()
        db.openDBs()

    def tearDown(self):
        db.closeDBs()
