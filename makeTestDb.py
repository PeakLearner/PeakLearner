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


dataPath = 'data'
testDbFile = 'test.db'

testDbPath = os.path.join(dataPath, testDbFile)


if os.path.exists(testDbFile):
    os.remove(testDbFile)

if os.path.exists(testDbPath):
    os.remove(testDbPath)

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

testapp = TestClient(app)

# query = {'url': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}
query = {'url': 'https://rcdata.nau.edu/genomic-ml/PeakSegFPOP/labels/H3K4me3_TDH_ENCODE/hub.txt'}

request = testapp.put('/uploadHubUrl', json=query)

assert request.status_code == 200

if os.path.exists(testDbFile):
    os.rename(testDbFile, testDbPath)
