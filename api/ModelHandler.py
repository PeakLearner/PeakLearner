import os
import PeakError
import threading
import api.plLocks as locks
import pandas as pd
import api.TrackHandler as th
import api.PLConfig as pl
import api.JobHandler as jh

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors', 'penalty', 'numPeaks']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']


def getModel(data):
    track, hub = data['name'].rsplit('/')

    data['hub'] = track

    data['track'] = hub

    problems = th.getProblems(data)

    output = []

    lock = locks.getLock(data['name'])

    lock.acquire()

    for problem in problems:
        # data path, hub path, track path, problem path
        modelsPath = '%s%s/%s/%s-%s-%s/' % (pl.dataPath, data['hub'], data['track'],
                                            problem['ref'], problem['start'], problem['end'])

        summaryPath = '%smodelSummary.txt' % modelsPath

        # Converter required because pandas will lose trailing 0's
        try:
            summary = pd.read_csv(summaryPath, sep='\t', header=None, converters={6: lambda x: str(x)})
        except FileNotFoundError:
            continue

        summary.columns = summaryColumns

        minError = summary[summary['errors'] == summary['errors'].min()]

        # Uses first penalty with min label error
        # This will favor the model with the lowest penalty, given that summary is sorted
        penalty = minError['penalty'].iloc[0]

        minErrorModelPath = '%s%s_Model.bedGraph' % (modelsPath, penalty)

        # TODO: If no good model, do LOPART

        model = loadModelFile(minErrorModelPath, data)

        output.extend(model)

    lock.release()

    return output


def loadModelFile(path, data):
    try:
        df = pd.read_csv(path, sep='\t', header=None)
    except FileNotFoundError:
        print("File", path, "not found")
        return []

    df.columns = ["ref", "start", "end", "type", "score"]

    df = df[df['type'] == 'peak']

    inView = df.apply(checkInBounds, axis=1, args=(data,))

    toView = df[inView]

    model = df[['ref', 'start', 'end', 'score']]

    return model.to_dict('records')


def checkInBounds(row, data):
    if not data['ref'] == row['ref']:
        return False

    startIn = (row['start'] >= data['start']) and (row['start'] <= data['end'])
    endIn = (row['end'] >= data['start']) and (row['end'] <= data['end'])
    wrap = (row['start'] < data['start']) and (row['end'] > data['end'])

    return startIn or endIn or wrap


def updateModelLabels(data, generate=True):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    # This is the problems that the label update is in
    problems = th.getProblems(data)

    threads = []

    for problem in problems:
        # data path, hub path, track path, problem path
        modelsPath = '%s%s/%s/%s-%s-%s/' % (pl.dataPath, data['hub'], data['track'],
                                            problem['ref'], problem['start'], problem['end'])

        if not os.path.exists(modelsPath):
            submitPregenJob(problem, data)
            continue

        files = os.listdir(modelsPath)

        summaryOutput = []

        labelQuery = {'name': data['name'], 'ref': problem['ref'], 'start': problem['start'], 'end': problem['end']}

        labels = pd.DataFrame(th.getLabels(labelQuery, useLock=False))

        labels.columns = ['chrom', 'chromStart', 'chromEnd', 'annotation']

        labels = labels[labels['annotation'] != 'unknown']

        summaryPath = '%smodelSummary.txt' % modelsPath

        for file in files:
            if '_Model' in file:
                penalty = getPenalty(file)

                modelPath = '%s%s' % (modelsPath, file)

                model = pd.read_csv(modelPath, sep='\t', header=None)

                model.columns = modelColumns

                peaks = model[model['annotation'] == 'peak']

                if peaks.size < 1:
                    os.remove(modelPath)
                    continue

                error = PeakError.error(peaks, labels)

                summary = PeakError.summarize(error)

                summary['penalty'] = penalty

                summary['numPeaks'] = len(peaks.index)

                summaryOutput.append(summary)

        try:
            problemSummary = pd.concat(summaryOutput)
        except ValueError:
            submitPregenJob(problem, data)
            continue

        problemSummary.to_csv(summaryPath, sep='\t', header=False, index=False)

        if generate:
            checkGenerateArgs = (problem, data, modelsPath)
            cgThread = threading.Thread(target=checkGenerateModels, args=checkGenerateArgs)
            threads.append(cgThread)
            cgThread.start()

    for thread in threads:
        thread.join()


def getPenalty(filePath):
    return filePath.rsplit('_', 1)[0]


def checkGenerateModels(problem, data, modelsPath):
    modelSummaryPath = '%s/modelSummary.txt' % modelsPath

    if not os.path.exists(modelSummaryPath):
        submitPregenJob(problem, data)
        return

    try:
        df = pd.read_csv(modelSummaryPath, sep='\t', header=None, converters={6: lambda x: str(x)})
    except pd.errors.EmptyDataError:
        # If no models to base errors off of, do pregen
        submitPregenJob(problem, data)
        return

    df.columns = summaryColumns

    df['floatPenalty'] = df['penalty'].astype(float)
    df = df.sort_values('floatPenalty', ignore_index=True)

    minError = df[df['errors'] == df['errors'].min()]

    if len(minError.index) > 1:
        # no need to generate new models if error is 0
        if minError.iloc[0]['errors'] == 0:
            return
        else:
            first = minError.iloc[0]
            last = minError.iloc[-1]

            biggerFp = first['fp'] > last['fp']
            smallerFn = first['fn'] < last['fn']

            # Sanity check for bad labels, if the minimum is still the same values
            # With little labels this could not generate new models
            if biggerFp or smallerFn:
                minPenalty = first['penalty']
                maxPenalty = last['penalty']
                submitGridSearch(problem, data, minPenalty, maxPenalty)

            return

    else:
        index = minError.index[0]

        model = minError.iloc[0]

        if model['fp'] > model['fn']:
            try:
                above = df.iloc[index + 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '*')
                return

            minPenalty = model['penalty']

            maxPenalty = above['penalty']

            # If the next model only has 1 more peak, not worth searching
            if model['numPeaks'] + 1 >= above['numPeaks']:
                return
        else:
            try:
                below = df.iloc[index - 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '/')
                return

            minPenalty = below['penalty']

            maxPenalty = model['penalty']

            # If the previous model is only 1 peak away, not worth searching
            if below['numPeaks'] + 1 >= model['numPeaks']:
                return

        submitGridSearch(problem, data, minPenalty, maxPenalty)

        return


def submitOOMJob(problem, data, penalty, jobType):
    job = {'type': 'model', 'problem': problem, 'trackInfo': data}

    if jobType == '*':
        job['penalty'] = float(penalty) * 10
    elif jobType == '/':
        job['penalty'] = float(penalty) / 10
    else:
        print("Invalid OOM Job")
        return
    jh.addJob(job)


def submitPregenJob(problem, data):
    job = {'type': 'pregen', 'problem': problem, 'trackInfo': data, 'penalties': getPrePenalties(problem, data)}
    jh.addJob(job)


def submitGridSearch(problem, data, minPenalty, maxPenalty, num=pl.gridSearchSize):
    job = {'type': 'gridSearch', 'problem': problem, 'trackInfo': data,
           'minPenalty': float(minPenalty), 'maxPenalty': float(maxPenalty), 'numModels': num}

    jh.addJob(job)


def putModel(data):
    modelData = data['modelData']
    modelInfo = data['modelInfo']
    problem = modelInfo['problem']
    trackInfo = modelInfo['data']
    penalty = data['penalty']

    trackPath = '%s%s/%s/' % (pl.dataPath, trackInfo['hub'], trackInfo['track'])
    problemPath = '%s%s-%d-%d/' % (trackPath, problem['ref'], problem['start'], problem['end'])

    if not os.path.exists(problemPath):
        try:
            os.makedirs(problemPath)
        except OSError:
            return

    lock = locks.getLock(trackInfo['name'])

    lock.acquire()

    modelFilePath = '%s%s_Model.bedGraph' % (problemPath, penalty)

    with open(modelFilePath, 'w') as f:
        f.writelines(modelData)

    # TODO: Only do this when a job that would put models is finished
    updateModelLabels(trackInfo, generate=False)

    lock.release()

    return modelInfo


def getPrePenalties(problem, data):
    genome = data['genome']

    # TODO: Make this actually learn based on previous data

    return [100, 1000, 10000, 100000, 1000000]
