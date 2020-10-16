import bbi
import os
import pandas as pd
import requests
import threading
import utils.SlurmConfig as cfg


def model(data, jobId):
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

    finishQuery = {'command': 'updateJob', 'args': {'id': jobId, 'status': 'Done'}}

    r = requests.post(cfg.remoteServer, json=finishQuery)

    if not r.status_code == 200:
        print("Model Request Error", r.status_code)

    if not cfg.testing:
        os.remove(coveragePath)


def generateModel(coveragePath, data, penalty):

    command = 'Rscript commands/GenerateModel.R %s %s' % (coveragePath, penalty)

    os.system(command)

    modelPath = '%s_penalty=%d_segments.bed' % (coveragePath, penalty)

    if os.path.exists(modelPath):
        sendModel(modelPath, data, penalty)


def sendModel(modelPath, modelInfo, penalty):
    modelData = []

    with open(modelPath) as model:
        data = model.readline()

        while not data == '':
            modelData.append(data)
            data = model.readline()

    query = {'command': 'putModel',
             'args': {'modelInfo': modelInfo, 'penalty': penalty, 'modelData': modelData}}

    r = requests.post(cfg.remoteServer, json=query)

    if not r.status_code == 200:
        print("Send Model Request Error", r.status_code)


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
                coverageInterval = coverage.fetch_intervals(problem['ref'], problem['start'], problem['end'], iterator=True)
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


def pregen(data, jobId):
    penalties = data['penalties']
    trackInfo = data['data']
    problem = data['problem']

    dataPath = '%s%s/%s-%d-%d/' % (cfg.dataPath, trackInfo['name'], problem['ref'], problem['start'], problem['end'])
    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
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

    finishQuery = {'command': 'updateJob', 'args': {'id': jobId, 'status': 'Done'}}

    r = requests.post(cfg.remoteServer, json=finishQuery)

    if not r.status_code == 200:
        print("Job Finish Request Error", r.status_code)

    if not cfg.testing:
        os.remove(coveragePath)
