import bbi
import os
import sys
import time
import numpy as np
import pandas as pd
import tempfile
import requests
import threading

try:
    import server.SlurmConfig as cfg
except ModuleNotFoundError:
    import SlurmConfig as cfg

modelGenPath = os.path.join('server', 'GenerateModel.R')


def model(job):
    data = job['jobData']

    dataPath = os.path.join(cfg.dataPath, 'PeakLearner-%s' % job['id'])

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            return False

    trackUrl = '%s%s/%s/%s/' % (cfg.remoteServer, job['user'], job['hub'], job['track'])
    getCoverageFile(job, dataPath, trackUrl)

    generateModel(dataPath, job, trackUrl)

    finishQuery = {'command': 'update', 'args': {'id': job['id'], 'status': 'Done'}}

    r = requests.post(cfg.jobUrl, json=finishQuery)

    if not r.status_code == 200:
        print("Model Request Error", r.status_code)


def generateModel(dataPath, stepData, trackUrl):
    coveragePath = os.path.join(dataPath, 'coverage.bedGraph')

    command = 'Rscript %s %s %f' % (modelGenPath, coveragePath, stepData['penalty'])

    os.system(command)

    segmentsPath = '%s_penalty=%f_segments.bed' % (coveragePath, stepData['penalty'])
    lossPath = '%s_penalty=%f_loss.tsv' % (coveragePath, stepData['penalty'])

    if os.path.exists(segmentsPath):
        sendSegments(segmentsPath, stepData, trackUrl)
    else:
        print("No segments output")

    # TODO: Send Loss?


def sendSegments(segmentsFile, stepData, trackUrl):
    strPenalty = str(stepData['penalty'])

    modelData = pd.read_csv(segmentsFile, sep='\t', header=None)

    modelInfo = {'user': stepData['user'],
                 'hub': stepData['hub'],
                 'track': stepData['track'],
                 'problem': stepData['jobData']['problem'],
                 'jobId': stepData['id']}

    modelUrl = '%smodels/' % trackUrl

    query = {'command': 'put',
             'args': {'modelInfo': modelInfo, 'penalty': strPenalty, 'modelData': modelData.to_json()}}

    r = requests.post(modelUrl, json=query)

    if r.status_code == 200:
        print('model successfully sent with penalty', strPenalty, 'and with modelInfo:\n', modelInfo, '\n')
        return

    if not r.status_code == 204:
        print("Send Model Request Error", r.status_code)


def getCoverageFile(job, dataPath, trackUrl):
    problem = job['jobData']['problem']

    requestUrl = '%s%s/' % (trackUrl, 'info')
    urlReq = requests.get(requestUrl)

    if not urlReq.status_code == 200:
        print("GetCoverageFile track Url Error", urlReq.status_code)
        return

    coveragePath = os.path.join(dataPath, 'coverage.bedGraph')

    coverageUrl = urlReq.json()['url']
    if not os.path.exists(coveragePath):
        with bbi.open(coverageUrl) as coverage:
            try:
                coverageInterval = coverage.fetch_intervals(problem['chrom'], problem['chromStart'],
                                                            problem['chromEnd'], iterator=True)
                return fixAndSaveCoverage(coverageInterval, coveragePath, problem)
            except KeyError:
                return

    return coveragePath


def fixAndSaveCoverage(interval, outputPath, problem):
    output = []

    prevEnd = problem['chromStart']

    for data in interval:
        # If current data's start doesn't have the previous end
        if prevEnd < data[1]:
            # Add zero valued data from prev end to current start
            output.append((problem['chrom'], prevEnd, data[1], 0))

        output.append(data)

        prevEnd = data[2]

    # If end of data doesn't completely go to end of problem
    # I don't think this is strictly necessary
    if prevEnd < problem['chromEnd']:
        # Output[0][0] = the chrom
        output.append((problem['chrom'], prevEnd, problem['chromEnd'], 0))

    output = pd.DataFrame(output)

    output.to_csv(outputPath, sep='\t', float_format='%d', header=False, index=False)

    return outputPath


def generateModels(job):
    data = job['jobData']
    penalties = data['penalties']

    dataPath = os.path.join(cfg.dataPath, 'PeakLearner-%s' % job['id'])
    trackUrl = '%s%s/%s/%s/' % (cfg.remoteServer, job['user'], job['hub'], job['track'])

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            return False

    coveragePath = getCoverageFile(job, dataPath, trackUrl)

    if not os.path.exists(coveragePath):
        return False

    modelThreads = []

    for penalty in penalties:
        modelData = job.copy()
        modelData['penalty'] = penalty

        modelArgs = (dataPath, modelData, trackUrl)

        modelThread = threading.Thread(target=generateModel, args=modelArgs)
        modelThreads.append(modelThread)
        modelThread.start()

    for thread in modelThreads:
        thread.join()

    finishQuery = {'command': 'update', 'args': {'id': job['id'], 'status': 'Done'}}

    r = requests.post(cfg.jobUrl, json=finishQuery)

    if not r.status_code == 200:
        print("Job Finish Request Error", r.status_code)
        return

    os.remove(coveragePath)


def gridSearch(job):
    data = job['jobData']
    minPenalty = data['minPenalty']
    maxPenalty = data['maxPenalty']
    numModels = job['numModels']
    # Remove start and end of list because that is minPenalty/maxPenalty (already calculated)
    # Add 2 to numModels to account for start/end points (already calculated models)
    data['penalties'] = np.linspace(minPenalty, maxPenalty, numModels + 2).tolist()[1:-1]

    generateModels(job)


def startJob(jobId):
    jobId = int(jobId)
    startTime = time.time()
    print("Starting job with ID", jobId)
    jobQuery = {'command': 'update', 'args': {'id': jobId, 'status': 'Processing'}}

    r = requests.post(cfg.jobUrl, json=jobQuery)

    if not r.status_code == 200:
        print("No job on server with job id", jobId)
        return

    job = r.json()

    startJobWithType(job)

    endTime = time.time()

    print("Start Time", startTime, "End Time", endTime, "total time", endTime - startTime)


def startJobWithType(job):
    types = {
        'model': model,
        'pregen': generateModels,
        'gridSearch': gridSearch
    }

    jobType = types.get(job['jobType'], None)

    jobType(job)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        startJob(sys.argv[1])
