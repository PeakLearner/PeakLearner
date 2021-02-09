import bbi
import os
import sys
import time
import numpy as np
import pandas as pd
import PeakSegDisk
import requests
import threading

try:
    import server.SlurmConfig as cfg
except ModuleNotFoundError:
    import SlurmConfig as cfg

genFeaturesPath = os.path.join('server', 'GenerateFeatures.R')


# Different Jobs
def predict(job, dataPath, coveragePath, trackUrl):
    modelUrl = '%smodels/' % trackUrl
    query = {'command': 'predict', 'args': job}

    r = requests.post(modelUrl, json=query)

    if r.json() is False:
        # No prediction can be made
        return

    job['penalty'] = 10 ** r.json()

    generateModel(dataPath, job, trackUrl)


def model(job, dataPath, coveragePath, trackUrl):
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


def generateModels(job, dataPath, coveragePath, trackUrl):
    data = job['jobData']
    penalties = data['penalties']

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


def gridSearch(job, dataPath, coveragePath, trackUrl):
    data = job['jobData']
    minPenalty = data['minPenalty']
    maxPenalty = data['maxPenalty']
    numModels = job['numModels']
    # Remove start and end of list because that is minPenalty/maxPenalty (already calculated)
    # Add 2 to numModels to account for start/end points (already calculated models)
    data['penalties'] = np.linspace(minPenalty, maxPenalty, numModels + 2).tolist()[1:-1]

    generateModels(job, dataPath, coveragePath, trackUrl)

# Helper Functions

def generateFeatureVec(job, dataPath, trackUrl):
    command = 'Rscript %s %s' % (genFeaturesPath, dataPath)
    os.system(command)

    featurePath = os.path.join(dataPath, 'features.tsv')

    featureDf = pd.read_csv(featurePath, sep='\t')

    featureQuery = {'command': 'put', 'args': {'data': featureDf.to_dict('records'),
                                               'problem': job['problem']}}

    featureUrl = '%sfeatures/' % trackUrl

    r = requests.post(featureUrl, json=featureQuery)

    if not r.status_code == 200:
        print('feature send error', r.status_code)
        return


def generateModel(dataPath, stepData, trackUrl):
    coveragePath = os.path.join(dataPath, 'coverage.bedGraph')

    segmentsPath = '%s_penalty=%f_segments.bed' % (coveragePath, stepData['penalty'])
    lossPath = '%s_penalty=%f_loss.tsv' % (coveragePath, stepData['penalty'])

    PeakSegDisk.FPOP_files(coveragePath, segmentsPath, lossPath, str(stepData['penalty']))

    if os.path.exists(segmentsPath):
        sendSegments(segmentsPath, stepData, trackUrl)
    else:
        raise Exception

    if not cfg.debug:
        os.remove(segmentsPath)
        os.remove(lossPath)

    # TODO: Send Loss?


def sendSegments(segmentsFile, stepData, trackUrl):
    strPenalty = str(stepData['penalty'])

    modelData = pd.read_csv(segmentsFile, sep='\t', header=None)
    modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
    sortedModel = modelData.sort_values('start', ignore_index=True)

    modelInfo = {'user': stepData['user'],
                 'hub': stepData['hub'],
                 'track': stepData['track'],
                 'problem': stepData['problem'],
                 'jobId': stepData['id']}

    modelUrl = '%smodels/' % trackUrl

    query = {'command': 'put',
             'args': {'modelInfo': modelInfo, 'penalty': strPenalty, 'modelData': sortedModel.to_json()}}

    r = requests.post(modelUrl, json=query)

    if r.status_code == 200:
        print('model successfully sent with penalty', strPenalty, 'and with modelInfo:\n', modelInfo, '\n')
        return

    if not r.status_code == 204:
        print("Send Model Request Error", r.status_code)


def getCoverageFile(job, dataPath, trackUrl):
    problem = job['problem']

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
    output.columns = ['chrom', 'chromStart', 'chromEnd', 'count']

    output.to_csv(outputPath, sep='\t', float_format='%d', header=False, index=False)

    return outputPath


def runJob(jobId):
    jobId = int(jobId)
    startTime = time.time()
    print("Starting job with ID", jobId)
    jobQuery = {'command': 'update', 'args': {'id': jobId, 'status': 'Processing'}}

    r = requests.post(cfg.jobUrl, json=jobQuery)

    if not r.status_code == 200:
        print("No job on server with job id", jobId)
        return

    job = r.json()



    dataPath = os.path.join(cfg.dataPath, 'PeakLearner-%s' % job['id'])

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            return False

    trackUrl = '%s%s/%s/%s/' % (cfg.remoteServer, job['user'], job['hub'], job['track'])

    coveragePath = getCoverageFile(job, dataPath, trackUrl)

    if not os.path.exists(coveragePath):
        return False

    if job['jobType'] == 'pregen' or job['jobType'] == 'predict':
        generateFeatureVec(job, dataPath, trackUrl)

    runJobWithType(job, dataPath, coveragePath, trackUrl)

    if not cfg.debug:
        os.remove(coveragePath)

        if job['jobType'] == 'pregen' or job['jobType'] == 'predict':
            featuresPath = os.path.join(dataPath, 'features.tsv')
            os.remove(featuresPath)

        os.remove(dataPath)

    endTime = time.time()

    print("total time", endTime - startTime)

    finishQuery = {'command': 'update', 'args': {'id': job['id'], 'status': 'Done'}}

    r = requests.post(cfg.jobUrl, json=finishQuery)

    if not r.status_code == 200:
        print("Job Finish Request Error", r.status_code)
        return


def runJobWithType(job, *args):
    types = {
        'model': model,
        'pregen': generateModels,
        'gridSearch': gridSearch,
        'predict': predict,
    }

    jobType = types.get(job['jobType'], None)

    jobType(job, *args)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        runJob(sys.argv[1])
