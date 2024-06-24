import os
import time
import shutil
import tarfile
import aiohttp
import unittest
import threading
import asynctest
from fastapi.testclient import TestClient

from core.util import PLConfig as cfg
from core.main import app
from core import database
from core import get_db

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbLogBackupDir = os.path.join(dataDir, 'db_log_backup')
testDataPath = os.path.join('tests', 'data')
testDbsPath = 'testDbs'


cfg.testing()
sleepTime = 600


class PeakLearnerTestBase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        if os.path.exists('test.db'):
            os.remove('test.db')
        shutil.copy(self.dbFile, '.')

        SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )

        TestingSessionLocal = sessionmaker(bind=engine)

        database.Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        self.app = app

        self.testapp = TestClient(self.app)

    def tearDown(self):
        if not os.path.exists(testDbsPath):
            os.makedirs(testDbsPath)
        shutil.move('test.db', os.path.join(testDbsPath, self._testMethodName + '.db'))


class PeakLearnerAsyncTestBase(asynctest.TestCase):
    async def setUp(self):
        if os.path.exists('test.db'):
            os.remove('test.db')
        shutil.copy(self.dbFile, '.')

        SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )

        TestingSessionLocal = sessionmaker(bind=engine)

        database.Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        self.app = app

    def tearDown(self):
        if not os.path.exists(testDbsPath):
            os.makedirs(testDbsPath)
        #shutil.move('test.db', os.path.join(testDbsPath, self._testMethodName + '.db'))
