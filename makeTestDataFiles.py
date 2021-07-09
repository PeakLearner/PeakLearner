import os
import time

import pandas as pd
import pytest
import tarfile
import shutil
import unittest
import requests
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

from core.util import PLConfig as cfg

cfg.testing()
sleepTime = 600

baseUrl = 'https://peaklearner.rc.nau.edu'


user = 'tristanmillerschool@gmail.com'
hub = 'H3K4me3_TDH_ENCODE'
hubURL = '%s/%s/%s/' % (baseUrl, user, hub)
axlTrackURL = '%s%s/' % (hubURL, 'aorta_ENCFF502AXL')
modelSumsUrl = '%smodelSum/' % axlTrackURL
lossUrl = '%sloss/' % axlTrackURL
featureUrl = '%sfeatures/' % axlTrackURL
jobsURL = '/Jobs/'
queueUrl = '%squeue/' % jobsURL

outputDir = os.path.join('tests', 'data')


config = testing.setUp()
app = get_app('production.ini')
from webtest import TestApp

testapp = TestApp(app)

out = testapp.get(queueUrl)

modelSums = pd.DataFrame()
losses = pd.DataFrame()
features = pd.DataFrame()

jobIds = []

while out.status_code == 200:
    job = out.json
    user = job['user']
    hub = job['hub']
    track = job['track']
    taskId = job['taskId']
    jobId = job['id']

    if jobId in jobIds:
        out = testapp.get(queueUrl)
        continue
    else:
        jobIds.append(jobId)

    jobs = testapp.get('/Jobs/', headers={'Accept': 'application/json'})

    newJobs = 0

    for serverJob in jobs.json:
        if serverJob['status'].lower() == 'new':
            newJobs += 1

    print('remaining Jobs:', newJobs)

    problem = job['problem']

    params = {'ref': problem['chrom'], 'start': problem['chromStart']}



    if job['type'] == 'model':
        params['penalty'] = job['penalty']

    with requests.get(featureUrl, params=params, headers={'Accept': 'application/json'}) as r:
        if r.status_code != 200:
            raise Exception

        feature = pd.Series(r.json())
        feature['user'] = user
        feature['hub'] = hub
        feature['track'] = track
        feature['ref'] = problem['chrom']
        feature['start'] = problem['chromStart']

        features = features.append(feature, ignore_index=True)

    with requests.get(modelSumsUrl, params=params, headers={'Accept': 'application/json'}) as r:
        if r.status_code != 200:
            raise Exception

        modelSum = pd.DataFrame(r.json())
        modelSum['user'] = user
        modelSum['hub'] = hub
        modelSum['track'] = track
        modelSum['ref'] = problem['chrom']
        modelSum['start'] = problem['chromStart']

        modelSums = modelSums.append(modelSum, ignore_index=True)

        def getLosses(row):

            lossParams = params.copy()
            lossParams['penalty'] = row['penalty']
            with requests.get(lossUrl, params=lossParams, headers={'Accept': 'application/json'}) as r:
                if r.status_code != 200:
                    raise

                loss = pd.Series(r.json())
                loss['user'] = user
                loss['hub'] = hub
                loss['track'] = track
                loss['ref'] = problem['chrom']
                loss['start'] = problem['chromStart']
                return loss

        losses = losses.append(modelSum.apply(getLosses, axis=1))

    out = testapp.get(queueUrl)

featuresPath = os.path.join(outputDir, 'features.csv')
modelSumsPath = os.path.join(outputDir, 'modelSums.csv')
lossPath = os.path.join(outputDir, 'losses.csv')

features.to_csv(featuresPath, sep='\t', index=False)
modelSums.to_csv(modelSumsPath, sep='\t', index=False)
losses.to_csv(lossPath, sep='\t', index=False)


