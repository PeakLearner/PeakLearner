import os
import PeakError
import pandas as pd
import api.TrackHandler as th
import api.PLConfig as pl
import api.JobHandler as jh

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors', 'penalty', 'numPeaks']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']


def getModel(data):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    problems = th.getProblems(data)

    output = []

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

        if len(minError.index) > 1:
            print("Multiple min")

        penalty = minError['penalty'].iloc[0]

        minErrorModelPath = '%s%s_Model.bedGraph' % (modelsPath, penalty)

        model = loadModelFile(minErrorModelPath, data)

        output.extend(model)

    return output


def loadModelFile(path, data):
    refseq = data['ref']
    start = data['start']
    end = data['end']

    output = []

    with open(path) as model:
        modelLine = model.readline()

        while not modelLine == '':
            lineVals = modelLine.split()
            lineStart = int(lineVals[1])
            lineEnd = int(lineVals[2])
            lineLabel = lineVals[3]

            lineIfStartIn = (lineStart >= start) and (lineStart <= end)
            lineIfEndIn = (lineEnd >= start) and (lineEnd <= end)
            wrap = (lineStart < start) and (lineEnd > end)

            if (lineIfStartIn or lineIfEndIn or wrap) and lineLabel == 'peak':
                lineHeight = float(lineVals[4])
                output.append({"ref": refseq, "start": lineStart,
                               "end": lineEnd, "score": lineHeight})

            modelLine = model.readline()

    return output


def updateModelLabels(data, generate=True):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    # This is the problems that the label update is in
    problems = th.getProblems(data)

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

        labels = pd.DataFrame(th.getLabels(labelQuery))
        labels.columns = ['chrom', 'chromStart', 'chromEnd', 'annotation']

        labels = labels[labels['annotation'] != 'unknown']

        summaryPath = '%smodelSummary.txt' % modelsPath

        for file in files:
            # If the file is a model
            # TODO: Make this smarter, only update relative models and/or prune models
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

        problemSummary = problemSummary.sort_values('penalty', ignore_index=True)

        problemSummary.to_csv(summaryPath, sep='\t', header=False, index=False)

        if generate:
            checkGenerateNewModels(problem, data, modelsPath)


def getPenalty(filePath):
    return filePath.rsplit('_', 1)[0]


def checkGenerateNewModels(problem, data, modelsPath):
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
    df = df.sort_values('penalty', ignore_index=True)

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
        else:
            try:
                below = df.iloc[index - 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '/')
                return

            minPenalty = below['penalty']

            maxPenalty = model['penalty']

        submitGridSearch(problem, data, minPenalty, maxPenalty)

        return


def submitOOMJob(problem, data, penalty, type):
    job = {'type': 'model', 'problem': problem, 'data': data}

    if type == '*':
        job['penalty'] = penalty * 10
    elif type == '/':
        job['penalty'] = penalty / 10
    else:
        print("Invalid OOM Job")
        return
    jh.addJob(job)


def submitPregenJob(problem, data):
    job = {'type': 'pregen', 'problem': problem, 'data': data, 'penalties': getPrePenalties(problem, data)}
    jh.addJob(job)


def submitGridSearch(problem, data, minPenalty, maxPenalty, num=pl.gridSearchSize):
    job = {'type': 'gridSearch', 'problem': problem, 'data': data,
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

    modelFilePath = '%s%s_Model.bedGraph' % (problemPath, penalty)

    with open(modelFilePath, 'w') as f:
        f.writelines(modelData)

    updateModelLabels(trackInfo, generate=False)

    return modelInfo


def getPrePenalties(problem, data):
    genome = data['genome']

    # TODO: Make this actually learn based on previous data

    return [100, 1000, 10000, 100000, 1000000]
