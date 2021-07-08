import json
import os
import time

import pandas as pd
import pytest
import tarfile
import shutil
import webtest
import pyramid
import unittest
import threading
import pyramid.paster
import pyramid.testing
from tests import Base

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbTar = os.path.join('data', 'db.tar.gz')
testDataPath = os.path.join('tests', 'data')

extraDataColumns = ['user', 'hub', 'track', 'ref', 'start']
featuresDf = pd.read_csv(os.path.join(testDataPath, 'features.csv'), sep='\t')
modelSumsDf = pd.read_csv(os.path.join(testDataPath, 'modelSums.csv'), sep='\t')
lossDf = pd.read_csv(os.path.join(testDataPath, 'losses.csv'), sep='\t')

useThreads = False


class PeakLearnerJobsTests(Base.PeakLearnerTestBase):
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'
    track = 'aorta_ENCFF115HTK'
    hubURL = '/%s/%s/' % (user, hub)
    labelURL = '%slabels/' % hubURL

    def setUp(self):
        super().setUp()

        self.config = pyramid.testing.setUp()
        self.app = pyramid.paster.get_app('production.ini')

        self.testapp = webtest.TestApp(self.app)

    def test_addHubLabel(self):
        label = {'ref': 'chr1', 'start': 15250059, 'end': 15251519, 'label': 'peakStart'}
        out = self.testapp.put_json(self.labelURL, label)

        assert out.status_code == 200

        return label

    def test_removeHubLabel(self):
        label = self.test_addHubLabel()

        out = self.testapp.delete_json(self.labelURL, label)

        assert out.status_code == 200

    def test_updateHubLabel(self):
        label = self.test_addHubLabel()
        label['label'] = 'peakEnd'

        out = self.testapp.post_json(self.labelURL, label)

        assert out.status_code == 200

    def test_getHubLabels(self):
        self.test_addHubLabel()

        range = {'ref': 'chr1', 'start': 0, 'end': 120000000}

        out = self.testapp.get(self.labelURL, params=range, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        assert len(out.json) != 0






