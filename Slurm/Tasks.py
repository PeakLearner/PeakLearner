import os
import sys
import time
import shutil
import requests
import subprocess
import PeakSegDisk
import pandas as pd
try:
    import SlurmConfig as cfg
except ModuleNotFoundError:
    import Slurm.SlurmConfig as cfg

genFeaturesPath = os.path.join('Slurm', 'GenerateFeatures.R')


def model(job, dataPath, coveragePath, trackUrl):
    task = job['task']
    segmentsPath = '%s_penalty=%s_segments.bed' % (coveragePath, task['penalty'])
    lossPath = '%s_penalty=%s_loss.tsv' % (coveragePath, task['penalty'])
    if cfg.debug:
        if os.path.exists(segmentsPath):
            return sendModel(segmentsPath, lossPath, job, trackUrl)
    try:
        PeakSegDisk.FPOP_files(coveragePath, segmentsPath, lossPath, str(task['penalty']))
    except FileNotFoundError:
        pass

    if os.path.exists(segmentsPath) or os.path.exists(lossPath):
        if not sendModel(segmentsPath, lossPath, job, trackUrl):
            return False
    else:
        return False

    if not cfg.debug:
        os.remove(segmentsPath)
        os.remove(lossPath)

    return True


def feature(job, dataPath, coveragePath, trackUrl):
    result = subprocess.run(['Rscript',
                             genFeaturesPath,
                             dataPath],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    featurePath = os.path.join(dataPath, 'features.tsv')

    if not os.path.exists(featurePath):
        print('out\n', result.stdout)
        print('err\n', result.stderr)

    featureDf = pd.read_csv(featurePath, sep='\t')

    featureQuery = {'data': featureDf.to_json(),
                    'problem': job['problem']}

    featureUrl = os.path.join(trackUrl, 'features')

    try:
        r = requests.put(featureUrl, json=featureQuery, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(featureQuery)

    if not r.status_code == 200:
        print(r.content)
        return False

    print("Sent feature for ", job)

    return True


def sendModel(segmentsFile, lossFile, job, trackUrl):
    task = job['task']
    modelData = pd.read_csv(segmentsFile, sep='\t', header=None)
    modelData.columns = ['chrom', 'start', 'end', 'annotation', 'mean']
    sortedModel = modelData.sort_values('start', ignore_index=True)
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

    modelUrl = os.path.join(trackUrl, 'models')

    query = {'problem': job['problem'], 'penalty': task['penalty'],
             'modelData': sortedModel.to_json(),
             'lossData': lossData.to_json()}

    try:
        r = requests.put(modelUrl, json=query, verify=cfg.verify)
    except requests.exceptions.ConnectionError:
        raise Exception(query)

    if r.status_code == 200:
        print('model successfully sent with penalty',
              task['penalty'],
              'and with modelInfo:\n',
              {'user': job['user'],
               'hub': job['hub'],
               'track': job['track'],
               'problem': job['problem'],
               'id': job['id'],
               'taskId': job['task']['id']},
              '\n')
        return True
    else:
        print(r.content)

    return False


def getCoverageFile(job, dataPath):
    problem = job['problem']

    coveragePath = os.path.join(dataPath, 'coverage.bedGraph')

    coverageUrl = job['url']

    leading, trailing = coverageUrl.split('://')

    # Make num timeouts configurable
    for i in range(1, 5):
        result = subprocess.run(['bin/bigWigToBedGraph',
                                 coverageUrl,
                                 coveragePath,
                                 '-chrom=%s' % problem['chrom'],
                                 '-start=%s' % str(problem['start']),
                                 '-end=%s' % str(problem['end'])],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not result.stderr == b'':
            print('download error\n', result.stderr)
            time.sleep(1)
            continue

        try:
            if not cfg.debug:
                tmpPath = os.path.join('/tmp', 'udcCache', leading, *trailing.split('/'))
                if os.path.exists(tmpPath):
                    shutil.rmtree(tmpPath)
            return fixCoverage(job, coveragePath)
        except pd.errors.EmptyDataError:
            return


def fixCoverage(job, coveragePath):
    problem = job['problem']
    coverage = pd.read_csv(coveragePath, sep='\t', header=None)
    coverage.columns = ['chrom', 'chromStart', 'chromEnd', 'count']

    chrom = coverage['chrom'].iloc[0]
    gapStarts = [problem['start'], ]
    gapStarts.extend(coverage['chromEnd'].tolist())
    gapEnds = coverage['chromStart'].tolist()
    gapEnds.append(problem['end'])

    data = {'chrom': chrom, 'chromStart': gapStarts, 'chromEnd': gapEnds}

    gaps = pd.DataFrame(data)
    gaps = gaps[gaps['chromStart'] < gaps['chromEnd']]

    gaps['count'] = 0

    fixedCoverage = pd.concat([gaps, coverage]).sort_values('chromStart', ignore_index=True)

    fixedCoverage.to_csv(coveragePath, sep='\t', header=False, index=False)

    return coveragePath


def runTask(job):
    trackUrl = os.path.join(cfg.remoteServer, job['user'], job['hub'], job['track'])

    task = job['task']

    dataPath = os.path.join(cfg.dataPath, 'PeakLearner-%s-%s' % (job['id'], task['id']))

    currentJobUrl = os.path.join(cfg.jobUrl, str(job['id']))

    if not os.path.exists(dataPath):
        try:
            os.makedirs(dataPath)
        except OSError:
            raise Exception

    coveragePath = getCoverageFile(job, dataPath)

    if coveragePath is not None:
        query = {'id': task['id'], 'status': 'Processing'}

        try:
            r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
        except requests.exceptions.ConnectionError:
            raise Exception(query)

        if r.status_code != 200:
            print(r.content)
            print(r.status_code)
            return False

        funcToRun = getTaskFunc(task)

        try:
            status = funcToRun(job, dataPath, coveragePath, trackUrl)
        except:
            if not cfg.debug:
                os.remove(coveragePath)
                shutil.rmtree(dataPath)
            raise

        endTime = time.time()

        if not cfg.debug:
            os.remove(coveragePath)
            shutil.rmtree(dataPath)

        if status:
            query = {'id': task['id'],
                     'status': 'Done'}

            try:
                r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
            except requests.exceptions.ConnectionError:
                raise Exception(query)

            if not r.status_code == 200:
                raise Exception(r.status_code)

            return True

        else:
            query = {'id': task['id'],
                     'status': 'Error'}
            try:
                r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
            except requests.exceptions.ConnectionError:
                raise Exception(query)

            if not r.status_code == 200:
                raise Exception(r.status_code)

            return False

    else:
        print('here?')
        if not cfg.debug:
            shutil.rmtree(dataPath)

        query = {'id': task['id'],
                 'status': 'NoData'}
        try:
            r = requests.post(currentJobUrl, json=query, verify=cfg.verify)
        except requests.exceptions.ConnectionError:
            raise Exception(query)

        if not r.status_code == 200:
            raise Exception(r.status_code)

        return False


def getTaskFunc(task):
    tasks = {'model': model,
             'feature': feature}
    return tasks[task['taskType']]
