import bbi
import os
import pandas as pd
import requests
import utils.SlurmConfig as cfg


def generateModel(data, jobId):
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

    command = 'Rscript commands/GenerateModel.R %s %s' % (coveragePath, penalty)

    os.system(command)

    modelPath = '%s_penalty=%d_segments.bed' % (coveragePath, penalty)

    if os.path.exists(modelPath):
        sendModel(modelPath, data)

    finishQuery = {'command': 'updateJob', 'args': {'id': jobId, 'status': 'Done'}}

    r = requests.post(cfg.remoteServer, json=finishQuery)

    if not r.status_code == 200:
        print("Request Error", r.status_code)


def sendModel(modelPath, modelInfo):
    modelData = []

    with open(modelPath) as model:
        data = model.readline()

        while not data == '':
            modelData.append(data)
            data = model.readline()

    query = {'command': 'putModel',
             'args': {'modelInfo': modelInfo, 'modelData': modelData}}

    r = requests.post(cfg.remoteServer, json=query)

    if not r.status_code == 200:
        print("Send Model Request Error", r.status_code)


def getCoverageFile(trackInfo, problem, output):

    query = {'command': 'getTrackUrl', 'args': trackInfo}

    hubInfo = requests.post(cfg.remoteServer, json=query)

    coveragePath = '%scoverage.bedGraph' % output

    if hubInfo.status_code == 204:
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


def pregenModels(data, jobId):
    print(data)
