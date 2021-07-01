import json
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

extraDataColumns = ['user', 'hub', 'track', 'ref', 'start']
featuresDf = pd.read_csv(os.path.join(testDataPath, 'features.csv'), sep='\t')
modelSumsDf = pd.read_csv(os.path.join(testDataPath, 'modelSums.csv'), sep='\t')
lossDf = pd.read_csv(os.path.join(testDataPath, 'losses.csv'), sep='\t')

useThreads = False

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




class PeakLearnerJobsTests(unittest.TestCase):
    jobsURL = '/Jobs/'
    queueUrl = '%squeue/' % jobsURL

    def setUp(self):
        self.config = testing.setUp()
        self.app = get_app('production.ini')
        from webtest import TestApp

        self.testapp = TestApp(self.app)

    def tearDown(self):
        if os.path.exists(dbDir):
            shutil.rmtree(dbDir)

    def getJobs(self):
        return self.testapp.get(self.jobsURL, headers={'Accept': 'application/json'})

    def test_getPotentialJobs(self):
        import core.Jobs.Jobs as Jobs
        job = {'user': 'Public',
                'hub': 'H3K4me3_TDH_ENCODE',
                'track': 'aorta_ENCFF115HTK',
                'problem': {'chrom': 'chr3',
                'chromStart': 93504854}}
        summary = self.getRelevantData(job, modelSumsDf)

        losses = self.getRelevantData(job, lossDf)

        # Add losses for submit search
        for loss in losses.to_dict('records'):
            loss = losses[losses['penalty'] == int(loss['penalty'])].astype(int)
            assert len(loss.index) == 1

            data = {'lossInfo': job, 'penalty': str(loss['penalty'].iloc[0]), 'lossData': loss.to_json()}

            json.dumps(data)

            lossUrl = '/%s/%s/%s/loss/' % (job['user'], job['hub'], job['track'])

            out = self.testapp.put_json(lossUrl, data)

            assert out.status_code == 200

        summary = summary.to_dict('records')

        # Single Model where penalty is
        for entry in summary:
            if entry['errors'] == 0:
                entry['errors'] += 1.0
                entry['fp'] += 1.0
                if entry['numPeaks'] > 1:
                    penalty = entry['penalty']

        data = {**job, 'sums': summary}

        out = self.testapp.put_json('/modelSumUpload/', data)

        assert out.status_code == 200

        contigJobs = {(job['user'], job['hub'], job['track'], job['problem']['chrom'], str(job['problem']['chromStart'])): []}

        out = Jobs.getPotentialJobs(contigJobs)

        assert len(out) == 1
        outJob = out[0]
        assert isinstance(outJob, Jobs.SingleModelJob)

        assert float(outJob.tasks['0']['penalty']) > penalty


        # Different case
        for entry in summary:
            if entry['errors'] == 1.0:
                entry['errors'] += 1.0
                entry['fn'] += 1.0
                if entry['numPeaks'] > 1:
                    penalty = entry['penalty']

        data = {**job, 'sums': summary}

        out = self.testapp.put_json('/modelSumUpload/', data)

        assert out.status_code == 200

        out = Jobs.getPotentialJobs(contigJobs)

        assert len(out) == 1

        outJob = out[0]

        assert isinstance(outJob, Jobs.GridSearchJob)

        # Different case
        for entry in summary:
            if entry['penalty'] == 100000:
                entry['errors'] += 1.0
                entry['fn'] += 1.0
                if entry['numPeaks'] > 1:
                    penalty = entry['penalty']

        data = {**job, 'sums': summary}

        out = self.testapp.put_json('/modelSumUpload/', data)

        assert out.status_code == 200

        out = Jobs.getPotentialJobs(contigJobs)

        print('getPotentialOut', out)

        assert len(out) == 1

        outJob = out[0]

        assert isinstance(outJob, Jobs.SingleModelJob)

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

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json

        assert len(jobs) == newJobLen

        for job in jobs:
            assert job['status'].lower() == 'done'

        self.testapp.get('/runJobSpawn/')

        out = self.getJobs()

        assert out.status_code == 200

        jobs = out.json

        # all jobs are done, more jobs should be spawned here because the job spawner was called
        assert len(jobs) != newJobLen

    def getRelevantData(self, job, data):
        user = data[data['user'] == job['user']]
        hub = user[user['hub'] == job['hub']]
        track = hub[hub['track'] == job['track']]
        chrom = track[track['ref'] == job['problem']['chrom']]
        out = chrom[chrom['start'] == job['problem']['chromStart']]

        return out.drop(columns=extraDataColumns)

    def putModelSum(self, job):
        sums = self.getRelevantData(job, modelSumsDf)

        if len(sums.index) < 1:
            raise Exception

        data = {**job, 'sums': sums.to_dict('records')}

        out = self.testapp.put_json('/modelSumUpload/', data)

        assert out.status_code == 200

    def putLoss(self, job, trackUrl):
        loss = self.getRelevantData(job, lossDf)
        loss = loss[loss['penalty'] == int(job['penalty'])]

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

        if int(taskId) == 0:
            self.putModelSum(job)

        if job['type'] == 'feature':
            self.putFeature(job, trackUrl)
        elif job['type'] == 'model':
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