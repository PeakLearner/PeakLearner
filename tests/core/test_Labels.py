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
    dbFile = os.path.join('data', 'test.db')
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'
    track = 'aorta_ENCFF115HTK'
    hubURL = os.path.join(user, hub)
    labelURL = os.path.join(hubURL, 'labels')
    badHubUrl = os.path.join('fake', hub)
    badLabelURL = os.path.join(badHubUrl, 'labels')
    rangeArgs = {'ref': 'chr1', 'start': 0, 'end': 120000000}

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

        out = self.testapp.delete(self.labelURL, json=label)

        assert out.status_code == 200

    def test_updateHubLabel(self):
        label = self.test_addHubLabel()
        label['label'] = 'peakEnd'

        out = self.testapp.post(self.labelURL, json=label)

        assert out.status_code == 200




