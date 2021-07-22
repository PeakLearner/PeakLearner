import json
import os
import time
import pytest
import tarfile
import shutil
import webtest
import pyramid
import unittest
import threading
import numpy as np
import pandas as pd
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
    jobsURL = '/Jobs/'
    queueUrl = '%squeue/' % jobsURL

    def setUp(self):
        super().setUp()

        self.config = pyramid.testing.setUp()
        self.app = pyramid.paster.get_app('production.ini')

        self.testapp = webtest.TestApp(self.app)

    def getJobs(self):
        return self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

    def test_featureJob(self):

        job = self.doPredictionFeatureStep()

        jobUrl = '%s%s/' % (self.jobsURL, job['id'])

        data = {'taskId': job['taskId'], 'status': 'Done', 'totalTime': '0'}

        out = self.testapp.post_json(jobUrl, data)

        assert out.status_code == 200

        job = out.json

        assert job['jobStatus'].lower() == 'done'

    def test_jobRestart(self):
        from core.Jobs import Jobs

        Jobs.makeJobHaveBadTime({})

        jobUrl = '%s0/' % self.jobsURL

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        jobToRestart = out.json

        assert jobToRestart['status'].lower() == 'queued'
        assert jobToRestart['lastModified'] == 0

        Jobs.checkRestartJobs({})

        out = self.testapp.get(jobUrl, headers={'Accept': 'application/json'})

        assert out.status_code == 200

        jobAfterRestart = out.json

        assert jobAfterRestart['status'].lower() == 'new'
        assert jobAfterRestart['lastModified'] != 0

    def doPredictionFeatureStep(self):
        # No Prediction Ready
        self.test_JobSpawner()

        out = self.testapp.get(self.queueUrl)

        assert out.status_code == 200

        predictionJob = out.json

        assert predictionJob['jobStatus'].lower() == 'queued'

        trackUrl = '/%s/%s/%s/' % (predictionJob['user'], predictionJob['hub'], predictionJob['track'])

        # Put a random feature there, really just to see that it works to begin with
        feature = featuresDf.sample()

        if len(feature.index) < 1:
            raise Exception

        data = {'data': feature.to_dict('records'),
                'problem': predictionJob['problem']}

        featureUrl = '%sfeatures/' % trackUrl

        out = self.testapp.put_json(featureUrl, data)

        assert out.status_code == 200

        return predictionJob

    def test_JobSpawner(self):
        out = self.getJobs()

        assert out.status_code == 200

        jobLen = len(out.json)

        self.testapp.get('/runJobSpawn/')

        out = self.getJobs()

        assert out.status_code == 200

        newJobLen = len(out.json)

        assert jobLen == newJobLen

        self.doJobsAsTheyCome()

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json

        # All the jobs should be done and moved to DoneJob
        assert len(jobs) == 0

        for job in jobs:
            assert job['status'].lower() == 'done'

        self.testapp.get('/runJobSpawn/')

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json

        # all jobs are done, more jobs should be spawned here because the job spawner was called
        assert len(jobs) != 0

    def test_getAllFeatures(self):
        self.test_featureJob()

        out = self.testapp.get('/features/')

        assert out.status_code == 200

        assert len(out.json) == 76

    def test_getAllModelSums(self):
        self.test_featureJob()

        out = self.testapp.get('/modelSums/')

        assert out.status_code == 200

        assert len(out.json) == 302

    def test_getAllLosses(self):
        self.test_featureJob()

        out = self.testapp.get('/losses/')

        assert out.status_code == 200

        assert len(out.json) == 300

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

        data = {**job, 'sum': sum.to_dict('records')}

        out = self.testapp.put_json('/modelSumUpload/', data)

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

        lossUrl = '%sloss/' % trackUrl

        out = self.testapp.put_json(lossUrl, data)

        assert out.status_code == 200

    def putFeature(self, job, trackUrl):
        feature = self.getRelevantData(job, featuresDf)

        if len(feature.index) < 1:
            raise Exception

        data = {'data': feature.to_dict('records'),
                'problem': job['problem']}

        featureUrl = '%sfeatures/' % trackUrl

        out = self.testapp.put_json(featureUrl, data)

        assert out.status_code == 200

    def doJob(self, job):

        jobId = job['id']
        taskId = job['taskId']
        user = job['user']
        hub = job['hub']
        track = job['track']
        problem = job['problem']

        trackUrl = '/%s/%s/%s/' % (user, hub, track)


        if job['type'] == 'feature':
            self.putFeature(job, trackUrl)
        elif job['type'] == 'model':
            self.putModelSum(job)
            self.putLoss(job, trackUrl)

        jobUrl = '%s%s/' % (self.jobsURL, job['id'])

        data = {'taskId': job['taskId'], 'status': 'Done', 'totalTime': '0'}

        out = self.testapp.post_json(jobUrl, data)

        assert out.status_code == 200

    def doJobsAsTheyCome(self):
        out = self.testapp.get(self.queueUrl)

        threads = []

        while out.status_code != 204:
            if useThreads:
                thread = threading.Thread(target=self.doJob, args=(out.json,))

                thread.start()

                threads.append(thread)
            else:
                self.doJob(out.json)

            out = self.testapp.get(self.queueUrl)

        if useThreads:
            for thread in threads:
                thread.join()