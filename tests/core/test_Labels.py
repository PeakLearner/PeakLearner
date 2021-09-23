import json
import os
import time

import pandas as pd
from tests import Base
from fastapi.testclient import TestClient

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
    hubURL = os.path.join(user, hub)
    labelURL = os.path.join(hubURL, 'labels')
    badHubUrl = os.path.join('fake', hub)
    badLabelURL = os.path.join(badHubUrl, 'labels')
    rangeArgs = {'ref': 'chr1', 'start': 0, 'end': 120000000}

    def setUp(self):
        super().setUp()

        import core.main as main

        self.app = main.app

        self.testapp = TestClient(self.app)

    def test_addHubLabel(self):
        label = {'ref': 'chr1', 'start': 15250059, 'end': 15251519, 'label': 'peakStart'}

        # Test label for non existant route
        out = self.testapp.put(self.badLabelURL, json=label)

        assert out.status_code == 404

        out = self.testapp.put(self.labelURL, json=label)

        assert out.status_code == 200

        return label

    def test_removeHubLabel(self):
        label = self.test_addHubLabel()

        labels = self.testapp.get(self.labelURL, params=self.rangeArgs, headers={'Accept': 'application/json'})

        labelsBefore = len(labels.json())

        out = self.testapp.delete(self.labelURL, json=label)

        assert out.status_code == 200

        labels = self.testapp.get(self.labelURL, params=self.rangeArgs, headers={'Accept': 'application/json'})

        assert len(labels.json()) < labelsBefore

    def test_updateHubLabel(self):
        label = self.test_addHubLabel()
        label['label'] = 'peakEnd'

        out = self.testapp.post(self.labelURL, json=label)

        assert out.status_code == 200

    def test_getHubLabels(self):
        self.test_addHubLabel()

        out = self.testapp.get(self.labelURL, params=self.rangeArgs, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        assert len(out.json()) != 0

        # Test get with contig
        out = self.testapp.get(self.labelURL, params={'contig': True}, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        assert len(out.json()) != 0

        # Test bad hub
        out = self.testapp.get(self.badLabelURL, params={'contig': True}, headers={'Accept': 'application/json'})

        assert out.status_code == 404




