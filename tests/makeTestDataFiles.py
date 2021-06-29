import os
import time

import pandas as pd
import pytest
import tarfile
import shutil
import unittest
import requests
import threading
from pyramid import testing
from pyramid.paster import get_app

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbTar = os.path.join('data', 'db.tar.gz')
testDataPath = os.path.join('tests', 'data')

if os.path.exists(dbDir):
    shutil.rmtree(dbDir)

if not os.path.exists(dbDir):
    with tarfile.open(dbTar) as tar:
        tar.extractall(dataDir)

from core.util import PLConfig as cfg

cfg.testing()
sleepTime = 600

baseUrl = 'https://peaklearner.rc.nau.edu'



class PeakLearnerTests(unittest.TestCase):
    user = 'tristanmillerschool@gmail.com'
    hub = 'H3K4me3_TDH_ENCODE'
    hubURL = '%s/%s/%s/' % (baseUrl, user, hub)
    axlTrackURL = '%s%s/' % (hubURL, 'aorta_ENCFF502AXL')
    modelSumsUrl = '%smodelSums/' % axlTrackURL
    jobsURL = '/Jobs/'
    queueUrl = '%squeue/' % jobsURL

    def setUp(self):
        self.config = testing.setUp()
        app = get_app('production.ini')
        from webtest import TestApp

        self.testapp = TestApp(app)


    def test_makeTestDataFiles(self):
        out = self.testapp.get(self.queueUrl)

        while out.status_code != 404:
            job = out.json
            user = job['user']
            hub = job['hub']
            track = job['track']
            taskId = job['taskId']
            jobId = job['id']

            params = {'ref': 'chr3', 'start': 93504854}

            if job['type'] == 'model':
                params['penalty'] = job['penalty']

            with requests.get(self.modelSumsUrl, params=params, headers={'Accept': 'application/json'}) as r:
                print(r.status_code)





            break

        assert 1 == 0

