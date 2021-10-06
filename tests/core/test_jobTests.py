import json
import os
import threading
import pandas as pd
import pytest
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
    jobsURL = '/Jobs'
    queueUrl = os.path.join(jobsURL, 'queue')

    def setUp(self):
        super().setUp()

        import core.main as main

        self.testapp = TestClient(main.app)

    def getJobs(self):
        return self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

    @pytest.mark.timeout(300)
    def test_featureJob(self):

        job = self.doPredictionFeatureStep()

        jobUrl = os.path.join(self.jobsURL, job['id'])

        data = {'taskId': job['taskId'], 'status': 'Done', 'totalTime': '0'}

        out = self.testapp.post(jobUrl, json=data)

        assert out.status_code == 200

        job = out.json()

        assert job['jobStatus'].lower() == 'done'

    @pytest.mark.timeout(300)
    def test_jobRestart(self):
        from core.Jobs import Jobs

        Jobs.makeJobHaveBadTime({})

        jobUrl = os.path.join(self.jobsURL, '0')

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        jobToRestart = out.json()

        assert jobToRestart['status'].lower() == 'queued'

        Jobs.checkRestartJobs({})

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        jobAfterRestart = out.json()

        assert jobAfterRestart['status'].lower() == 'new'
        assert jobAfterRestart['lastModified'] != 0

    def doPredictionFeatureStep(self):
        # No Prediction Ready
        self.test_JobSpawner()

        out = self.testapp.get(self.queueUrl)

        assert out.status_code == 200

        predictionJob = out.json()

        assert predictionJob['jobStatus'].lower() == 'queued'

        trackUrl = os.path.join(predictionJob['user'], predictionJob['hub'], predictionJob['track'])

        # Put a random feature there, really just to see that it works to begin with
        feature = featuresDf.sample()

        if len(feature.index) < 1:
            raise Exception

        data = {'data': feature.to_dict('records'),
                'problem': predictionJob['problem']}

        featureUrl = os.path.join(trackUrl, 'features')

        out = self.testapp.put(featureUrl, json=data)

        assert out.status_code == 200

        return predictionJob

    @pytest.mark.timeout(300)
    def test_JobSpawner(self):
        out = self.getJobs()

        assert out.status_code == 200

        jobLen = len(out.json())

        out = self.testapp.get('/runJobSpawn/')

        assert out.status_code == 200

        out = self.getJobs()

        assert out.status_code == 200

        newJobLen = len(out.json())

        assert jobLen == newJobLen

        self.doJobsAsTheyCome()

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json()

        # All the jobs should be done and moved to DoneJob
        assert len(jobs) == 0

        for job in jobs:
            assert job['status'].lower() == 'done'

        out = self.testapp.get('/runJobSpawn/')

        assert out.status_code == 200

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json()

        # all jobs are done, more jobs should be spawned here because the job spawner was called
        assert len(jobs) != 0

    @pytest.mark.timeout(300)
    def test_getAllFeatures(self):
        self.test_featureJob()

        out = self.testapp.get('/features', timeout=60)

        assert out.status_code == 200

        assert len(out.json()) == 75

    @pytest.mark.timeout(300)
    def test_getAllModelSums(self):
        self.test_featureJob()

        out = self.testapp.get('/modelSums', timeout=60)

        assert out.status_code == 200

        assert len(out.json()) == 302

    @pytest.mark.timeout(300)
    def test_getAllLosses(self):
        self.test_featureJob()

        out = self.testapp.get('/losses', timeout=60)

        assert out.status_code == 200

        assert len(out.json()) == 300

    def getRelevantData(self, job, data):
        user = data[data['user'] == job['user']]
        hub = user[user['hub'] == job['hub']]
        track = hub[hub['track'] == job['track']]
        chrom = track[track['ref'] == job['problem']['chrom']]
        out = chrom[chrom['start'] == job['problem']['chromStart']]

        return out.drop(columns=extraDataColumns)

    def putModelSum(self, job):
        sums = self.getRelevantData(job, modelSumsDf)

        sum = sums[abs(sums['penalty'] - float(job['penalty'])) <= 0.00001]

        if len(sum.index) < 1:
            raise Exception

        data = {**job, 'sum': sum.to_json()}

        out = self.testapp.put('/modelSumUpload', json=data)

        assert out.status_code == 200

    def putLoss(self, job, trackUrl):
        loss = self.getRelevantData(job, lossDf)
        loss = loss[abs(loss['penalty'] - float(job['penalty'])) <= 0.00001]

        if len(loss.index) < 1:
            raise Exception

        lossInfo = {'user': job['user'],
                    'hub': job['hub'],
                    'track': job['track'],
                    'problem': job['problem']}

        data = {'lossInfo': lossInfo, 'penalty': job['penalty'], 'lossData': loss.to_json()}

        lossUrl = os.path.join(trackUrl, 'loss')

        out = self.testapp.put(lossUrl, json=data)

        assert out.status_code == 200

    def putFeature(self, job, trackUrl):
        feature = self.getRelevantData(job, featuresDf)

        if len(feature.index) < 1:
            raise Exception

        data = {'data': feature.to_dict('records'),
                'problem': job['problem']}

        featureUrl = os.path.join(trackUrl, 'features')

        out = self.testapp.put(featureUrl, json=data)

        assert out.status_code == 200

    def doJob(self, job):
        jobId = job['id']
        taskId = job['taskId']
        user = job['user']
        hub = job['hub']
        track = job['track']
        problem = job['problem']

        trackUrl = os.path.join(user, hub, track)

        if job['type'] == 'feature':
            self.putFeature(job, trackUrl)
        elif job['type'] == 'model':
            self.putModelSum(job)
            self.putLoss(job, trackUrl)

        jobUrl = os.path.join(self.jobsURL, job['id'])

        data = {'taskId': job['taskId'], 'status': 'Done', 'totalTime': '0'}

        out = self.testapp.post(jobUrl, json=data)

        assert out.status_code == 200

    def doJobsAsTheyCome(self):
        out = self.testapp.get(self.queueUrl)

        threads = []

        while out.status_code != 204:
            if useThreads:
                thread = threading.Thread(target=self.doJob, args=(out.json(),))

                thread.start()

                threads.append(thread)
            else:
                self.doJob(out.json())

            out = self.testapp.get(self.queueUrl)

        if useThreads:
            for thread in threads:
                thread.join()