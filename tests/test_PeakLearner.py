import os
import time
import pytest
import tarfile
import shutil
import unittest
import threading
from pyramid import testing
from pyramid.paster import get_app

dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbTar = os.path.join('data', 'db.tar.gz')

if os.path.exists(dbDir):
    shutil.rmtree(dbDir)

if not os.path.exists(dbDir):
    with tarfile.open(dbTar) as tar:
        tar.extractall(dataDir)

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


class PeakLearnerTests(unittest.TestCase):
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'
    testHub = 'TestHub'
    track = 'aorta_ENCFF115HTK'
    hubURL = '/%s/%s/' % (user, hub)
    testHubURL = '/%s/%s/' % (user, testHub)
    trackURL = '%s%s/' % (hubURL, track)
    trackInfoURL = '%sinfo/' % trackURL
    labelURL = '%slabels/' % trackURL
    modelsUrl = '%smodels/' % trackURL
    jobsURL = '/Jobs/'
    rangeArgs = {'ref': 'chr1', 'start': 0, 'end': 120000000, 'label': 'peakStart'}
    startLabel = rangeArgs.copy()
    startLabel['start'] = 15250059
    startLabel['end'] = 15251519
    endLabel = startLabel.copy()
    endLabel['start'] = 15251599
    endLabel['end'] = 15252959
    endLabel['label'] = 'peakEnd'
    noPeakLabel = startLabel.copy()
    noPeakLabel['start'] = 16089959
    noPeakLabel['end'] = 16091959
    noPeakLabel['label'] = 'noPeak'

    def setUp(self):
        self.config = testing.setUp()
        app = get_app('production.ini')
        from webtest import TestApp

        self.testapp = TestApp(app)

    def test_serverWorking(self):
        res = self.testapp.get('/')
        assert res.status_code == 200

    def test_addHub(self):
        query = {'url': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}

        request = self.testapp.put('/uploadHubUrl/', query)

        assert request.status_code == 200

        assert request.json == self.testHubURL

        dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

        assert os.path.exists(dataPath)

        hg19path = os.path.join(dataPath, 'genomes', 'hg19')

        assert os.path.exists(hg19path)

        problemsTrackList = os.path.join(hg19path, 'problems', 'trackList.json')

        assert os.path.exists(problemsTrackList)

    def test_getHubInfo(self):
        expectedTrackKeys = ['aorta_ENCFF115HTK', 'aorta_ENCFF502AXL', 'aorta_ENCFF974KVN',
                             'aorta_Input_ENCFF209QWM', 'aorta_Input_ENCFF264DFJ', 'aorta_Input_ENCFF626FKO',
                             'colon_ENCFF332UYK', 'colon_ENCFF873WWR', 'colon_Input_ENCFF788LJE',
                             'colon_Input_ENCFF937EBV', 'skeletalMuscle_ENCFF000BMB', 'skeletalMuscle_ENCFF000BMD',
                             'skeletalMuscle_ENCFF063EVY', 'skeletalMuscle_ENCFF280HQO',
                             'skeletalMuscle_ENCFF290WZR', 'skeletalMuscle_ENCFF743PUV',
                             'skeletalMuscle_Input_ENCFF000BJZ', 'skeletalMuscle_Input_ENCFF000BKA',
                             'skeletalMuscle_Input_ENCFF003XTF', 'skeletalMuscle_Input_ENCFF208RCO',
                             'thyroid_ENCFF014AIG', 'thyroid_ENCFF020VFT', 'thyroid_ENCFF482XRP',
                             'thyroid_ENCFF606GLK', 'thyroid_Input_ENCFF054RMF',
                             'thyroid_Input_ENCFF108SOQ', 'thyroid_Input_ENCFF442YKA', 'thyroid_Input_ENCFF995SFR']
        hubInfoURL = '%sinfo/' % self.hubURL
        request = self.testapp.get(hubInfoURL)

        assert request.status_code == 200

        requestOutput = request.json

        print(requestOutput)

        assert requestOutput['genome'] == 'hg19'

        assert len(requestOutput['tracks']) == 28
        for trackKey in requestOutput['tracks']:
            assert trackKey in expectedTrackKeys

    def getJobs(self):
        return self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

    def getLabels(self, params):
        return self.testapp.get(self.labelURL, params=params, headers={'Accept': 'application/json'})

    def test_labels(self):
        request = self.getJobs()

        numJobsBefore = len(request.json['jobs'])

        # Blank Label Test
        request = self.getLabels(params=self.rangeArgs)

        numLabelsBefore = len(request.json)

        # Add label
        request = self.testapp.put_json(self.labelURL, self.startLabel)

        # Check Label Added
        request = self.getLabels(params=self.rangeArgs)

        assert request.status_code == 200

        assert len(request.json) == numLabelsBefore + 1

        numLabelsBefore = len(request.json)

        serverLabel = request.json[0]

        assert serverLabel['ref'] == self.startLabel['ref']
        assert serverLabel['start'] == self.startLabel['start']
        assert serverLabel['end'] == self.startLabel['end']
        assert serverLabel['label'] == 'peakStart'

        request = self.getJobs()

        assert request.status_code == 200

        assert len(request.json['jobs']) == numJobsBefore + 1

        numJobsBefore = len(request.json['jobs'])

        # Try adding another label
        request = self.testapp.put_json(self.labelURL, self.endLabel)

        assert request.status_code == 200

        request = self.getLabels(params=self.rangeArgs)

        assert request.status_code == 200

        assert len(request.json) == numLabelsBefore + 1

        # Update second label
        updateAnother = self.endLabel.copy()
        updateAnother['label'] = 'peakEnd'

        request = self.testapp.put_json(self.labelURL, updateAnother)

        assert request.status_code == 200

        request = self.getJobs()

        # Check that system doesn't create duplicate jobs
        assert len(request.json['jobs']) == numJobsBefore

        request = self.getLabels(params=self.rangeArgs)

        assert request.status_code == 200

        assert len(request.json) == numLabelsBefore + 1

        # Remove Labels
        for label in request.json:
            request = self.testapp.delete_json(self.labelURL, params=label)

            assert request.status_code == 200

        request = self.getLabels(params=self.rangeArgs)

        # No Content, No Body
        assert request.status_code == 204

    def test_putModel(self):


