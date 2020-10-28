import bbi
import os
import sys
import numpy as np
import pandas as pd
import requests
import threading
import utils.SlurmConfig as cfg


def model(job):
    data = job['data']
    problem = data['problem']
    trackInfo = data['data']
    penalty = data['penalty']

    dataPath = '%s%s/%s-%d-%d/' % (cfg.dataPath, trackInfo['name'], problem['ref'], problem['start'], problem['end'])

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            return

    coveragePath = getCoverageFile(trackInfo, problem, dataPath)

    generateModel(coveragePath, data, penalty)

    finishQuery = {'command': 'updateJob', 'args': {'id': job['id'], 'status': 'Done'}}

    r = requests.post(cfg.remoteServer, json=finishQuery)

    if not r.status_code == 200:
        print("Model Request Error", r.status_code)

    if not cfg.debug:
        os.remove(coveragePath)


def generateModel(coveragePath, data, penalty):

    command = 'Rscript commands/GenerateModel.R %s %f' % (coveragePath, penalty)

    os.system(command)

    modelPath = '%s_penalty=%f_segments.bed' % (coveragePath, penalty)

    if os.path.exists(modelPath):
        sendModel(modelPath, data, penalty)


def sendModel(modelPath, modelInfo, penalty):
    modelData = []

    strPenalty = str(penalty)

    with open(modelPath) as model:
        data = model.readline()

        while not data == '':
            modelData.append(data)
            data = model.readline()

    query = {'command': 'putModel',
             'args': {'modelInfo': modelInfo, 'penalty': strPenalty, 'modelData': modelData}}

    r = requests.post(cfg.remoteServer, json=query)

    if not r.status_code == 200:
        print("Send Model Request Error", r.status_code)

    if not cfg.debug:
        os.remove(modelPath)


def getCoverageFile(trackInfo, problem, output):

    query = {'command': 'getTrackUrl', 'args': trackInfo}

    hubInfo = requests.post(cfg.remoteServer, json=query)

    coveragePath = '%scoverage.bedGraph' % output

    if not hubInfo.status_code == 200:
        print("GetCoverageFile Hub info Error", hubInfo.status_code)
        return

    coverageUrl = hubInfo.json()
    if not os.path.exists(coveragePath):
        with bbi.open(coverageUrl) as coverage:
            try:
                coverageInterval = coverage.fetch_intervals(problem['ref'], problem['start'],
                                                            problem['end'], iterator=True)
                return fixAndSaveCoverage(coverageInterval, coveragePath, problem)
            except KeyError:
                return

    return coveragePath


def fixAndSaveCoverage(interval, outputPath, problem):
    output = []

    prevEnd = problem['start']

    for data in interval:
        # If current data's start doesn't have the previous end
        if prevEnd < data[1]:
            # Add zero valued data from prev end to current start
            output.append((problem['ref'], prevEnd, data[1], 0))

        output.append(data)

        prevEnd = data[2]

    # If end of data doesn't completely go to end of problem
    # I don't think this is strictly necessary
    if prevEnd < problem['end']:
        # Output[0][0] = the chrom
        output.append((problem['ref'], prevEnd, problem['end'], 0))

    output = pd.DataFrame(output)

    output.to_csv(outputPath, sep='\t', float_format='%d', header=False, index=False)

    return outputPath


def generateModels(job, report=True):
    data = job['data']
    penalties = data['penalties']
    trackInfo = data['data']
    problem = data['problem']

    dataPath = '%s%s/%s-%d-%d/' % (cfg.dataPath, trackInfo['name'], problem['ref'], problem['start'], problem['end'])
    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            print("Os Error")
            return

    coveragePath = getCoverageFile(data['data'], data['problem'], dataPath)

    modelThreads = []

    for penalty in penalties:
        modelData = data
        modelData['penalty'] = penalty

        modelArgs = (coveragePath, modelData, penalty)

        modelThread = threading.Thread(target=generateModel, args=modelArgs)
        modelThread.start()
        modelThreads.append(modelThread)

    for thread in modelThreads:
        thread.join()

    if report:

        finishQuery = {'command': 'updateJob', 'args': {'id': job['id'], 'status': 'Done'}}

        r = requests.post(cfg.remoteServer, json=finishQuery)

        if not r.status_code == 200:
            print("Job Finish Request Error", r.status_code)

    if not cfg.debug:
        os.remove(coveragePath)


def gridSearch(job):
    data = job['data']
    minPenalty = data['minPenalty']
    maxPenalty = data['maxPenalty']
    numModels = data['numModels']
    # Remove start and end of list because that is minPenalty/maxPenalty (already calculated)
    data['penalties'] = np.linspace(minPenalty, maxPenalty, numModels + 2).tolist()[1:-1]

    generateModels(job, report=False)

    finishQuery = {'command': 'updateJob', 'args': {'id': job['id'], 'status': 'Done'}}

    r = requests.post(cfg.remoteServer, json=finishQuery)

    if not r.status_code == 200:
        print("Shotgun Job Finish Request Error", r.status_code)


def startJob(jobId):
    jobQuery = {'command': 'getJob', 'args': {'id': jobId}}

    r = requests.post(cfg.remoteServer, json=jobQuery)

    if not r.status_code == 200:
        print("No job on server with job id", jobId)
        return

    job = r.json()

    if not job['status'].lower() == 'new':
        return

    startJobWithType(job)


def startJobWithType(job):
    types = {
        'model': model,
        'pregen': generateModels,
        'gridSearch': gridSearch
    }

    jobType = types.get(job['data']['type'], None)

    jobType(job)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        startJob(sys.argv[2])