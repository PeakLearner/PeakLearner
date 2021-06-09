import os
import sys
import time
import shutil
import requests
import subprocess
import PeakSegDisk
import pandas as pd
import SlurmConfig as cfg

genFeaturesPath = os.path.join('Slurm', 'GenerateFeatures.R')


def model(task, dataPath, coveragePath, trackUrl):
    segmentsPath = '%s_penalty=%s_segments.bed' % (coveragePath, task['penalty'])
    lossPath = '%s_penalty=%s_loss.tsv' % (coveragePath, task['penalty'])
    try:
        PeakSegDisk.FPOP_files(coveragePath, segmentsPath, lossPath, str(task['penalty']))
    except FileNotFoundError:
        pass

    if os.path.exists(lossPath):
        if not sendLoss(lossPath, task, trackUrl):
            return False
    else:
        return False

    if os.path.exists(segmentsPath):
        if not sendSegments(segmentsPath, task, trackUrl):
            return False
    else:
        return False

    if not cfg.debug:
        os.remove(segmentsPath)
        os.remove(lossPath)

    return True


def feature(task, dataPath, coveragePath, trackUrl):
    result = subprocess.run(['Rscript',
                             genFeaturesPath,
                             dataPath],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    featurePath = os.path.join(dataPath, 'features.tsv')

    if not os.path.exists(featurePath):
        print('out\n', result.stdout)
        print('err\n', result.stderr)

    featureDf = pd.read_csv(featurePath, sep='\t')

    featureQuery = {'data': featureDf.to_dict('records'),
                    'problem': task['problem']}

    featureUrl = '%sfeatures/' % trackUrl

    try:
        r = requests.put(featureUrl, json=featureQuery, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(featureQuery)

    if not r.status_code == 200:
        return False

    print("Sent feature for ", task)

    return True


def sendSegments(segmentsFile, task, trackUrl):
    modelData = pd.read_csv(segmentsFile, sep='\t', header=None)
    modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
    sortedModel = modelData.sort_values('start', ignore_index=True)

    modelInfo = {'user': task['user'],
                 'hub': task['hub'],
                 'track': task['track'],
                 'problem': task['problem'],
                 'jobId': task['id']}

    modelUrl = '%smodels/' % trackUrl

    query = {'modelInfo': modelInfo, 'penalty': task['penalty'], 'modelData': sortedModel.to_json()}

    try:
        r = requests.put(modelUrl, json=query, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(query)

    if r.status_code == 200:
        print('model successfully sent with penalty', task['penalty'], 'and with modelInfo:\n', modelInfo, '\n')
        return True

    return False


def sendLoss(lossFile, task, trackUrl):
    strPenalty = str(task['penalty'])
    lossUrl = '%sloss/' % trackUrl

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

    lossInfo = {'user': task['user'],
                'hub': task['hub'],
                'track': task['track'],
                'problem': task['problem'],
                'jobId': task['id']}

    query = {'lossInfo': lossInfo, 'penalty': strPenalty, 'lossData': lossData.to_json()}

    try:
        r = requests.put(lossUrl, json=query, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(query)

    if r.status_code == 200:
        print('loss successfully sent with penalty', strPenalty, 'and with lossInfo:\n', lossInfo, '\n')
        return True

    return True


def getCoverageFile(task, dataPath):
    problem = task['problem']

    coveragePath = os.path.join(dataPath, 'coverage.bedGraph')

    coverageUrl = task['trackUrl']

    # Make num timeouts configurable
    for i in range(1, 5):
        result = subprocess.run(['bin/bigWigToBedGraph',
                                 coverageUrl,
                                 coveragePath,
                                 '-chrom=%s' % problem['chrom'],
                                 '-start=%s' % str(problem['chromStart']),
                                 '-end=%s' % str(problem['chromEnd'])],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not result.stderr == b'':
            print('download error\n', result.stderr)
            time.sleep(1)
            continue

        if os.path.exists(coveragePath):
            break

        # wait a second then make the request again
        time.sleep(1)

    return fixCoverage(task, coveragePath)


def fixCoverage(task, coveragePath):
    problem = task['problem']
    coverage = pd.read_csv(coveragePath, sep='\t', header=None)
    coverage.columns = ['chrom', 'chromStart', 'chromEnd', 'count']

    chrom = coverage['chrom'].iloc[0]
    gapStarts = [problem['chromStart'], ]
    gapStarts.extend(coverage['chromEnd'].tolist())
    gapEnds = coverage['chromStart'].tolist()
    gapEnds.append(problem['chromEnd'])

    data = {'chrom': chrom, 'chromStart': gapStarts, 'chromEnd': gapEnds}

    gaps = pd.DataFrame(data)
    gaps = gaps[gaps['chromStart'] < gaps['chromEnd']]

    gaps['count'] = 0

    fixedCoverage = pd.concat([gaps, coverage]).sort_values('chromStart', ignore_index=True)

    fixedCoverage.to_csv(coveragePath, sep='\t', header=False, index=False)

    return coveragePath


def runTask(task):
    trackUrl = '%s%s/%s/%s/' % (cfg.remoteServer, task['user'], task['hub'], task['track'])

    dataPath = os.path.join(cfg.dataPath, 'PeakLearner-%s-%s' % (task['id'], task['taskId']))

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            raise Exception

    startTime = time.time()

    coveragePath = getCoverageFile(task, dataPath)

    queueTime = time.time()

    query = {'taskId': task['taskId'], 'status': 'Processing', 'queuedTime': queueTime - startTime}

    currentJobUrl = '%s%s/' % (cfg.jobUrl, task['id'])

    try:
        r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(query)

    task = r.json()

    funcToRun = getTaskFunc(task)

    status = funcToRun(task, dataPath, coveragePath, trackUrl)

    endTime = time.time()

    totalTime = endTime - startTime

    if not cfg.debug:
        os.remove(coveragePath)
        shutil.rmtree(dataPath)

    if status:
        query = {'id': task['id'],
                 'taskId': task['taskId'],
                 'status': 'Done',
                 'totalTime': str(totalTime)}
        try:
            r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
        except requests.exceptions.ConnectionError:
            raise Exception(query)

        if not r.status_code == 200:
            raise Exception(r.status_code)

        return True

    query = {'id': task['id'],
             'taskId': task['taskId'],
             'status': 'Error',
             'totalTime': str(totalTime)}
    try:
        r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(query)

    if not r.status_code == 200:
        raise Exception(r.status_code)


def getTaskFunc(task):
    tasks = {'model': model,
             'feature': feature}

    return tasks[task['type']]
