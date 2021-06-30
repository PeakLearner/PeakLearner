import os
import time

import pandas as pd
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
testDataPath = os.path.join('tests', 'data')

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
    sampleTrack = 'aorta_ENCFF502AXL'
    hubURL = '/%s/%s/' % (user, hub)
    testHubURL = '/%s/%s/' % (user, testHub)
    trackURL = '%s%s/' % (hubURL, track)
    axlTrackURL = '%s%s/' % (hubURL, 'aorta_ENCFF502AXL')
    sampleTrackURL = '%s%s/' % (hubURL, sampleTrack)
    trackInfoURL = '%sinfo/' % trackURL
    labelURL = '%slabels/' % trackURL
    modelsUrl = '%smodels/' % trackURL
    sampleModelsUrl = '%smodels/' % sampleTrackURL
    jobsURL = '/Jobs/'
    queueUrl = '%squeue/' % jobsURL
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

    def test_AddHubAndEnvSetup(self):
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

        numJobsBefore = len(request.json)

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

        assert len(request.json) == numJobsBefore + 1

        numJobsBefore = len(request.json)

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
        assert len(request.json) == numJobsBefore

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

    def test_doSampleJob(self):
        modelsPath = os.path.join(testDataPath, 'Models')
        dirs = os.listdir(modelsPath)

        for jobDir in dirs:
            a, jobId, taskId = jobDir.split('-')

            jobDir = os.path.join(modelsPath, jobDir)

            jobUrl = self.jobsURL + jobId + '/'

            output = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

            job = output.json

            task = job['tasks'][taskId]

            trackUrl = '/%s/%s/%s/' % (job['user'], job['hub'], job['track'])

            if task['type'] == 'model':
                fileBase = os.path.join(jobDir, 'coverage.bedGraph_penalty=%s_' % task['penalty'])
                segmentsFile = fileBase + 'segments.bed'
                lossFile = fileBase + 'loss.tsv'

                # Upload Model

                modelData = pd.read_csv(segmentsFile, sep='\t', header=None)
                modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
                sortedModel = modelData.sort_values('start', ignore_index=True)

                modelInfo = {'user': job['user'],
                             'hub': job['hub'],
                             'track': job['track'],
                             'problem': job['problem'],
                             'jobId': job['id']}

                modelUrl = '%smodels/' % trackUrl

                query = {'modelInfo': modelInfo, 'penalty': task['penalty'], 'modelData': sortedModel.to_json()}
                output = self.testapp.put_json(modelUrl, query)
                assert output.status_code == 200

                # Upload Loss

                strPenalty = str(task['penalty'])
                lossUrl = '%sloss/' % trackUrl

                lossData = pd.read_csv(lossFile, sep='\t', header=None)
                lossData.columns = ['penalty',
                                    'segments',
                                    'peaks',
                                    'totalBases',
                                    'bedGraphLines',
                                    'meanPenalizedCost',
                                    'totalUnpenalizedCost',
                                    'numConstraints',
                                    'meanIntervals',
                                    'maxIntervals']

                lossInfo = {'user': job['user'],
                            'hub': job['hub'],
                            'track': job['track'],
                            'problem': job['problem'],
                            'jobId': job['id']}

                query = {'lossInfo': lossInfo, 'penalty': strPenalty, 'lossData': lossData.to_json()}

                output = self.testapp.put_json(lossUrl, query)
                assert output.status_code == 200
            if task['type'] == 'feature':
                featurePath = os.path.join(jobDir, 'features.tsv')
                featureDf = pd.read_csv(featurePath, sep='\t')

                featureQuery = {'data': featureDf.to_dict('records'),
                                'problem': job['problem']}

                featureUrl = '%sfeatures/' % trackUrl

                output = self.testapp.put_json(featureUrl, featureQuery)

                assert output.status_code == 200

    def test_getPeakLearnerModels(self):
        self.test_doSampleJob()

        params = {'ref': 'chr3', 'start': 0,
                  'end': 396044860}

        output = self.testapp.get(self.sampleModelsUrl, params=params, headers={'Accept': '*/*'})

        assert output.status_code == 200

    def test_labelsWithAcceptAnyHeader(self):
        params = {'ref': 'chr3', 'start': 0,
                  'end': 396044860}

        output = self.testapp.get(self.labelURL, params=params, headers={'Accept': '*/*'})

        assert output.status_code == 200

    def test_get_features(self):
        self.test_doSampleJob()
        params = {'ref': 'chr3', 'start': 93504854}

        featureUrl = '%sfeatures/' % self.axlTrackURL

        out = self.testapp.get(featureUrl, params=params)

        assert out.status_code == 200

        assert len(out.json.keys()) > 1

        otherParams = params.copy()

        otherParams['start'] += 1

        out = self.testapp.get(featureUrl, params=otherParams)

        assert out.status_code == 204

    def test_get_loss(self):
        self.test_doSampleJob()
        params = {'ref': 'chr3', 'start': 93504854, 'penalty': '10000'}

        lossUrl = '%sloss/' % self.axlTrackURL

        out = self.testapp.get(lossUrl, params=params)

        assert out.status_code == 200

        loss = out.json

        assert len(loss.keys()) > 1

        assert int(params['penalty']) == loss['penalty']

    def test_get_modelSum(self):
        self.test_doSampleJob()
        params = {'ref': 'chr3', 'start': 93504854}

        modelSumsUrl = '%smodelSum/' % self.axlTrackURL

        out = self.testapp.get(modelSumsUrl, params=params)

        assert len(out.json) != 0

    def test_unlabeledRegion(self):
        unlabeledUrl = '%sunlabeled/' % self.hubURL

        output = self.testapp.get(unlabeledUrl)

        should = ['ref', 'start', 'end']

        for key in output.json:
            assert key in should

        hubInfoURL = '%sinfo/' % self.hubURL
        request = self.testapp.get(hubInfoURL)

        hubInfo = request.json

        for track in hubInfo['tracks']:
            trackLabelsUrl = '%s%s/labels/' % (self.hubURL, track)

            out = self.testapp.get(trackLabelsUrl, params=output.json, headers={'Accept': 'application/json'})

            # No Content
            assert out.status_code == 204

    def test_labeledRegion(self):
        unlabeledUrl = '%slabeled/' % self.hubURL

        output = self.testapp.get(unlabeledUrl)

        should = ['ref', 'start', 'end']

        for key in output.json:
            assert key in should

        hubInfoURL = '%sinfo/' % self.hubURL
        request = self.testapp.get(hubInfoURL)

        hubInfo = request.json

        labelsExist = False

        for track in hubInfo['tracks']:
            trackLabelsUrl = '%s%s/labels/' % (self.hubURL, track)

            out = self.testapp.get(trackLabelsUrl, params=output.json, headers={'Accept': 'application/json'})

            if out.status_code == 204:
                continue

            if out.status_code == 200:
                if len(out.json) > 0:
                    labelsExist = True

        assert labelsExist

    def test_getTrackJob(self):
        jobsUrl = '%sjobs/' % self.trackURL

        output = self.testapp.get(jobsUrl, params=self.rangeArgs)

        assert len(output.json) != 0

    def test_GetTrackModelSums(self):

        jobsUrl = '%smodelSums/' % self.axlTrackURL

        modelRegion = {'ref': 'chr3', 'start': 93504854, 'end': 194041961}

        output = self.testapp.get(jobsUrl, params=modelRegion)

        # There should be no models at this point
        assert len(output.json) == 0

        self.test_doSampleJob()

        output = self.testapp.get(jobsUrl, params=modelRegion)

        # There should be no models at this point

        assert len(output.json) != 0

    def test_stats_page(self):
        output = self.testapp.get('/stats/')

        assert output.status_code == 200

    def test_model_stats_page(self):
        output = self.testapp.get('/stats/model/')

        assert output.status_code == 200

    def test_label_stats_page(self):
        output = self.testapp.get('/stats/label/')

        assert output.status_code == 200

    def test_jobs_stats_page(self):
        output = self.testapp.get('/Jobs/', headers={'Accept': 'text/html'})

        assert output.status_code == 200

    def test_about_page(self):
        out = self.testapp.get('/about/')

        assert out.status_code == 200

    def test_myHubs_page(self):
        out = self.testapp.get('/myHubs/')

        assert out.status_code == 200

    def doJobsAsTheyCome(self):
        out = self.testapp.get(self.queueUrl)

        while out.status_code != 404:
            currentJob = out.json
            print(currentJob)
            break

    def test_jobSpawner(self):
        out = self.getJobs()

        assert out.status_code == 200

        jobLen = len(out.json)

        self.testapp.get('/runJobSpawn/')

        out = self.getJobs()

        assert out.status_code == 200

        newJobLen = len(out.json)

        assert jobLen == newJobLen

        self.doJobsAsTheyCome()

        assert 1 == 0


    def test_makeTestDataFiles(self):
        out = self.testapp.get(self.queueUrl)

        while out.status_code != 404:
            currentJob = out.json
            print(currentJob)
            break
