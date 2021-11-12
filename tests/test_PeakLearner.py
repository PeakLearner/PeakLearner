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
        hubInfoURL = '%s/info' % self.hubURL

        request = self.testapp.get(hubInfoURL)

        assert request.status_code == 200

        requestOutput = request.json()

        assert requestOutput['genome'] == 'hg19'

        assert len(requestOutput['tracks']) == 28
        for trackKey in requestOutput['tracks']:
            assert trackKey in expectedTrackKeys

    def getJobs(self):
        return self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

    def getLabels(self, params):
        return self.testapp.get(self.labelURL, params=params, headers={'Accept': 'application/json'})

    def test_labels(self):
        # Blank Label Test
        rangeQuery = self.rangeArgs.copy()
        del rangeQuery['label']

        request = self.getLabels(params=rangeQuery)

        assert request.status_code == 200

        numLabelsBefore = len(request.json())

        # Add label
        request = self.testapp.put(self.labelURL, json=self.startLabel)

        assert request.status_code == 200

        # Check Label Added
        request = self.getLabels(params={**self.rangeArgs, 'contig': True})

        assert request.status_code == 200

        assert len(request.json()) == numLabelsBefore + 1

        numLabelsBefore = len(request.json())

        serverLabel = request.json()[0]

        assert serverLabel['ref'] == self.startLabel['ref']
        assert serverLabel['start'] == self.startLabel['start']
        assert serverLabel['end'] == self.startLabel['end']
        assert serverLabel['label'] == 'peakStart'

        # Try adding another label
        request = self.testapp.put(self.labelURL, json=self.endLabel)

        assert request.status_code == 200

        request = self.getLabels(params=self.rangeArgs)

        assert request.status_code == 200

        assert len(request.json()) == numLabelsBefore + 1

        # Update second label
        updateAnother = self.endLabel.copy()
        updateAnother['label'] = 'peakEnd'

        request = self.testapp.post(self.labelURL, json=updateAnother)

        assert request.status_code == 200

        request = self.getLabels(params=self.rangeArgs)

        assert request.status_code == 200

        assert len(request.json()) == numLabelsBefore + 1

        assert request.status_code == 200

        # Remove Labels
        for label in request.json():
            request = self.testapp.delete(self.labelURL, json=label)

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

            jobUrl = os.path.join(self.jobsURL, jobId)

            output = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

            job = output.json()

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

                modelUrl = '%smodels' % trackUrl

                query = {'modelInfo': modelInfo, 'penalty': task['penalty'], 'modelData': sortedModel.to_json()}
                output = self.testapp.put(modelUrl, json=query)
                assert output.status_code == 200

                # Upload Loss

                strPenalty = str(task['penalty'])
                lossUrl = '%sloss' % trackUrl

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

                output = self.testapp.put(lossUrl, json=query)

                assert output.status_code == 200
            if task['type'] == 'feature':
                featurePath = os.path.join(jobDir, 'features.tsv')
                featureDf = pd.read_csv(featurePath, sep='\t')

                featureQuery = {'data': featureDf.to_dict('records'),
                                'problem': job['problem']}

                featureUrl = '%sfeatures' % trackUrl

                output = self.testapp.put(featureUrl, json=featureQuery)

                assert output.status_code == 200

    def test_modelWithNoPeaksError(self):
        self.test_doSampleJob()

        user = 'Public'
        hub = 'H3K4me3_TDH_ENCODE'
        track = 'aorta_ENCFF502AXL'
        problem = {'ref': 'chr3', 'start': 93504854, 'chromEnd': 194041961}

        testUrl = '/%s' % os.path.join(user, hub, track)
        testModelSumUrl = os.path.join(testUrl, 'modelSum')

        r = self.testapp.get(testModelSumUrl, params=problem)

        assert r.status_code == 200

        out = r.json()

        for sum in out:
            if sum['penalty'] == '1000000':
                assert sum['errors'] > 1

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

        featureUrl = os.path.join(self.axlTrackURL, 'features')

        out = self.testapp.get(featureUrl, params=params)

        assert out.status_code == 200

        assert len(out.json().keys()) > 1

        otherParams = params.copy()

        otherParams['start'] += 1

        out = self.testapp.get(featureUrl, params=otherParams)

        assert out.status_code == 204

    def test_getPredictionModel(self):
        # Put test model
        testProblem = {'chrom': 'chr17', 'chromStart': 62460760, 'chromEnd': 77546461}
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

        modelInfo = {'user': self.user,
                     'hub': self.hub,
                     'track': self.track,
                     'problem': testProblem}

        query = {'modelInfo': modelInfo, 'penalty': 57094.997295, 'modelData': sortedModel.to_json()}
        output = self.testapp.put(self.modelsUrl, json=query)
        assert output.status_code == 200

        # Get test model

        getQuery = {'ref': testProblem['chrom'], 'start': testProblem['chromStart'], 'end': testProblem['chromEnd']}
        output = self.testapp.get(self.modelsUrl, params=getQuery)

        assert output.status_code == 200

        assert len(output.json()) > 0

    def test_get_loss(self):
        self.test_doSampleJob()
        params = {'ref': 'chr3', 'start': 93504854, 'penalty': '10000'}

        lossUrl = os.path.join(self.axlTrackURL, 'loss')

        out = self.testapp.get(lossUrl, params=params)

        assert out.status_code == 200

        loss = out.json()

        assert len(loss.keys()) > 1

        assert int(params['penalty']) == loss['penalty']

    def test_get_modelSum(self):
        self.test_doSampleJob()
        params = {'ref': 'chr3', 'start': 93504854}

        modelSumsUrl = os.path.join(self.axlTrackURL, 'modelSum')

        out = self.testapp.get(modelSumsUrl, params=params)

        assert out.status_code == 200

        assert len(out.json()) != 0

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

    def test_getTrackJob(self):
        jobsUrl = os.path.join(self.trackURL, 'jobs')

        output = self.testapp.get(jobsUrl, params=self.rangeArgs)

        assert output.status_code == 200

        assert len(output.json()) != 0

    def test_GetTrackModelSums(self):

        modelSumUrl = os.path.join(self.axlTrackURL, 'modelSums')

        modelRegion = {'ref': 'chr3', 'start': 93504854, 'end': 194041961}

        output = self.testapp.get(modelSumUrl, params=modelRegion)

        # No Models at this point
        assert output.status_code == 204

        self.test_doSampleJob()

        output = self.testapp.get(modelSumUrl, params=modelRegion)

        assert output.status_code == 200

        # There should be models at this point

        assert len(output.json()) != 0

    def test_predictionModel(self):
        modelsPath = os.path.join(testDataPath, 'Models')

        jobDir = 'PeakLearner-7-1'

        jobDir = os.path.join(modelsPath, jobDir)

        penalty = 1000

        fileBase = os.path.join(jobDir, 'coverage.bedGraph_penalty=%s_' % penalty)
        segmentsFile = fileBase + 'segments.bed'

        # Upload Model

        modelData = pd.read_csv(segmentsFile, sep='\t', header=None)
        modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
        sortedModel = modelData.sort_values('start', ignore_index=True)

        sortedModel['chrom'] = 'chr2'

        problemWithNoLabels = {'chrom': 'chr2', 'chromStart': 149790582, 'chromEnd': 234003741}

        modelInfo = {'user': self.user,
                     'hub': self.hub,
                     'track': self.track,
                     'problem': problemWithNoLabels}

        modelUrl = os.path.join(self.trackURL, 'models')

        query = {'modelInfo': modelInfo, 'penalty': penalty, 'modelData': sortedModel.to_json()}
        output = self.testapp.put(modelUrl, json=query)
        assert output.status_code == 200

        params = {'ref': problemWithNoLabels['chrom'],
                  'start': problemWithNoLabels['chromStart'], 'end': problemWithNoLabels['chromEnd']}

        modelOut = self.testapp.get(modelUrl, params=params, headers={'Accept': 'application/json'})

        assert modelOut.status_code == 200

        assert len(modelOut.json()) != 0

    def test_flopart_model(self):
        data = {'ref': 'chr3',
                'start': 128660000,
                'end': 165420000,
                'modelType': 'FLOPART',
                'scale': 5e-05,
                'visibleStart': 134540000,
                'visibleEnd': 152920000}

        labels = [{'ref': 'chr3', 'start': 143679399, 'end': 143691199, 'label': 'peakStart'},
                  {'ref': 'chr3', 'start': 143691399, 'end': 143703399, 'label': 'peakEnd'},
                  {'ref': 'chr3', 'start': 143704399, 'end': 143707399, 'label': 'noPeaks'}]
        trackUrl = '/%s' % os.path.join('Public', 'H3K4me3_TDH_ENCODE', 'aorta_ENCFF115HTK')
        labelUrl = os.path.join(trackUrl, 'labels')
        modelUrl = os.path.join(trackUrl, 'models')

        for label in labels:
            request = self.testapp.put(labelUrl, json=label)

            assert request.status_code == 200

        request = self.testapp.get(modelUrl, params=data)

        if not request.status_code == 200:
            print(request.content)

        assert request.status_code == 200




    def test_stats_page(self):
        output = self.testapp.get('/stats/')

        assert output.status_code == 200

    def test_log_file_clean(self):

        assert not os.path.exists(Base.dbLogBackupDir)

        from core.util import PLdb as db

        db.cleanLogs()

        assert os.path.exists(Base.dbLogBackupDir)

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
