import os
import pandas as pd
from tests import Base
from core.util import PLConfig as cfg
from fastapi.testclient import TestClient

testDataPath = os.path.join('tests', 'data')

extraDataColumns = ['user', 'hub', 'track', 'ref', 'start']
featuresDf = pd.read_csv(os.path.join(testDataPath, 'features.csv'), sep='\t')
modelSumsDf = pd.read_csv(os.path.join(testDataPath, 'modelSums.csv'), sep='\t')
lossDf = pd.read_csv(os.path.join(testDataPath, 'losses.csv'), sep='\t')

cfg.testing()
sleepTime = 600

lockDetect = True


class PeakLearnerTests(Base.PeakLearnerTestBase):
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'
    testHub = 'TestHub'
    track = 'aorta_ENCFF115HTK'
    sampleTrack = 'aorta_ENCFF502AXL'
    hubURL = '/%s/%s' % (user, hub)
    testHubURL = '/%s/%s' % (user, testHub)
    trackURL = '%s/%s' % (hubURL, track)
    axlTrackURL = '%s/%s' % (hubURL, 'aorta_ENCFF502AXL')
    sampleTrackURL = '%s/%s' % (hubURL, sampleTrack)
    trackInfoURL = '%s/info' % trackURL
    labelURL = '%s/labels' % trackURL
    modelsUrl = '%s/models' % trackURL
    sampleModelsUrl = '%s/models' % sampleTrackURL
    jobsURL = '/Jobs'
    queueUrl = '%s/queue' % jobsURL
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

    def test_serverWorking(self):
        res = self.testapp.get('/')
        assert res.status_code == 200

    def test_AddHubAndEnvSetup(self):
        query = {'url': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}

        request = self.testapp.put('/uploadHubUrl', json=query)

        assert request.status_code == 200

        dataPath = cfg.dataPath

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
        hubInfoURL = '%s/info' % self.hubURL

        request = self.testapp.get(hubInfoURL)

        assert request.status_code == 200

        requestOutput = request.json()

        assert requestOutput['genome'] == 'hg19'

        assert len(requestOutput['tracks']) == 24
        for trackKey in requestOutput['tracks']:
            assert trackKey in expectedTrackKeys

    def getLabels(self, params):
        return self.testapp.get(self.labelURL, params=params, headers={'Accept': 'application/json'})

    def test_get_label(self):
        # Blank Label Test
        rangeQuery = self.rangeArgs.copy()
        del rangeQuery['label']

        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        assert len(request.json()) != 0

    def test_a_put_label(self):
        request = self.testapp.put(self.labelURL, json=self.startLabel)

        assert request.status_code == 200

    def test_update_label(self):
        rangeQuery = self.rangeArgs.copy()
        del rangeQuery['label']
        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        toUpdate = request.json()[0]
        oldLabel = toUpdate['label']
        oldId = toUpdate['label_id']

        del toUpdate['lastModified']
        del toUpdate['lastModifiedBy']
        del toUpdate['label_id']

        toUpdate['label'] = 'peakStart'

        request = self.testapp.post(self.labelURL, json=toUpdate)

        assert request.status_code == 200

        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        for label in request.json():
            if label['label_id'] == oldId:
                assert label['label'] != oldLabel

    def test_delete_label(self):
        rangeQuery = self.rangeArgs.copy()
        del rangeQuery['label']
        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        labelsBefore = len(request.json())

        toDelete = request.json()[0]
        oldId = toDelete['label_id']

        del toDelete['lastModified']
        del toDelete['lastModifiedBy']
        del toDelete['label_id']

        request = self.testapp.delete(self.labelURL, json=toDelete)

        assert request.status_code == 200

        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        labels = request.json()

        assert labelsBefore == len(labels) + 1

        for label in labels:
            assert label['label_id'] != oldId

    def test_put_model(self):
        sampleDir = os.path.join('tests', 'data', 'Models', 'PeakLearner-7-1')
        modelPath = os.path.join(sampleDir, 'coverage.bedGraph_penalty=1000_segments.bed')
        modelData = pd.read_csv(modelPath, sep='\t', header=None)
        modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
        sortedModel = modelData.sort_values('start', ignore_index=True)
        problem = {'chrom': 'chr3', 'start': 93504854, 'end': 194041961}
        trackUrl = '/%s/%s/%s/' % (self.user, self.hub, self.track)
        modelUrl = '%smodels' % trackUrl

        lossPath = os.path.join(sampleDir, 'coverage.bedGraph_penalty=1000_loss.tsv')
        lossData = pd.read_csv(lossPath, sep='\t', header=None)
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

        query = {'problem': problem, 'penalty': '1000',
                 'modelData': sortedModel.to_json(),
                 'lossData': lossData.to_json()}
        output = self.testapp.put(modelUrl, json=query)

        if output.status_code != 200:
            print(output.content)
        assert output.status_code == 200

    def test_put_features(self):
        sampleDir = os.path.join('tests', 'data', 'Models', 'PeakLearner-7-0')
        featurePath = os.path.join(sampleDir, 'features.tsv')
        featureDf = pd.read_csv(featurePath, sep='\t')
        problem = {'chrom': 'chr3', 'start': 93504854, 'end': 194041961}
        trackUrl = '/%s/%s/%s/' % (self.user, self.hub, self.track)
        featuresUrl = '%sfeatures' % trackUrl

        query = {'data': featureDf.to_json(),
                 'problem': problem}
        output = self.testapp.put(featuresUrl, json=query)

        if output.status_code != 200:
            print(output.content)
        assert output.status_code == 200

    def test_labelsWithAcceptAnyHeader(self):
        params = {'ref': 'chr3', 'start': 0,
                  'end': 396044860}

        output = self.testapp.get(self.labelURL, params=params, headers={'Accept': '*/*'})

        assert output.status_code == 200

    def test_getPredictionModel(self):
        # Put test model
        testProblem = {'chrom': 'chr17', 'start': 62460760, 'end': 77546461}
        sampleDir = os.path.join('tests', 'data', 'Models', 'PeakLearner-7-1')
        lossPath = os.path.join(sampleDir, 'coverage.bedGraph_penalty=1000_loss.tsv')
        lossData = pd.read_csv(lossPath, sep='\t', header=None)
        modelData = pd.DataFrame([{'chrom': 'chr17',
                                   'start': 62500000,
                                   'end': 62550000,
                                   'annotation': 'background',
                                   'mean': 0.1},
                                  {'chrom': 'chr17',
                                   'start': 62550001,
                                   'end': 62600000,
                                   'annotation': 'peak',
                                   'mean': 15},
                                  {'chrom': 'chr17',
                                   'start': 62600001,
                                   'end': 62650000,
                                   'annotation': 'background',
                                   'mean': 0.1}
                                  ])

        modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
        sortedModel = modelData.sort_values('start', ignore_index=True)

        query = {'problem': testProblem, 'penalty': '1000',
                 'modelData': sortedModel.to_json(),
                 'lossData': lossData.to_json()}
        output = self.testapp.put(self.modelsUrl, json=query)
        assert output.status_code == 200

        # Get test model

        getQuery = {'ref': testProblem['chrom'], 'start': testProblem['start'], 'end': testProblem['end']}
        output = self.testapp.get(self.modelsUrl, params=getQuery)

        assert output.status_code == 200

        assert len(output.json()) > 0

    def test_unlabeledRegion(self):
        unlabeledUrl = os.path.join(self.hubURL, 'unlabeled')

        output = self.testapp.get(unlabeledUrl)

        assert output.status_code == 200

        should = ['ref', 'start', 'end']

        for key in output.json():
            assert key in should

        hubInfoURL = os.path.join(self.hubURL, 'info')
        request = self.testapp.get(hubInfoURL)

        assert request.status_code == 200

        hubInfo = request.json()

        for track in hubInfo['tracks']:
            trackLabelsUrl = os.path.join(self.hubURL, track, 'labels')

            out = self.testapp.get(trackLabelsUrl, params=output.json(), headers={'Accept': 'application/json'})

            # No Content
            if out.status_code == 200:
                print(output.json())
                print(out.json())
            assert out.status_code == 204

    def test_labeledRegion(self):
        labeledUrl = os.path.join(self.hubURL, 'labeled')

        output = self.testapp.get(labeledUrl)

        should = ['ref', 'start', 'end']

        for key in output.json():
            assert key in should

        hubInfoURL = os.path.join(self.hubURL, 'info')
        request = self.testapp.get(hubInfoURL)

        hubInfo = request.json()

        labelsExist = False

        for track in hubInfo['tracks']:
            trackLabelsUrl = os.path.join(self.hubURL, track, 'labels')

            out = self.testapp.get(trackLabelsUrl, params=output.json(), headers={'Accept': 'application/json'})

            if out.status_code == 204:
                continue

            if out.status_code == 200:
                if len(out.json()) > 0:
                    labelsExist = True

        assert labelsExist

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

    def test_get_jobs(self):
        out = self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        assert out.json() != 0

    def test_queue_task(self):
        queueUrl = os.path.join(self.jobsURL, 'queue')

        out = self.testapp.get(queueUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

    def test_update_task(self):
        jobUrl = os.path.join(self.jobsURL, '1')

        out = self.testapp.post(jobUrl, json={'status': 'Queued'})

        assert out.status_code == 200

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        job = out.json()

        assert job['task']['status'] == 'Queued'

    def test_finish_task(self):
        jobUrl = os.path.join(self.jobsURL, '1')

        out = self.testapp.post(jobUrl, json={'status': 'Done'})

        assert out.status_code == 200

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        job = out.json()