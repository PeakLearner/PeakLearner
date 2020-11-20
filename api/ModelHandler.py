import PeakError
import threading
import tempfile
import pandas as pd
import api.TrackHandler as th
import api.PLConfig as pl
import api.JobHandler as jh
from api import PLdb as db

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
jbrowseModelColumns = ["ref", "start", "end", "type", "score"]


def getModel(data):
    data['hub'], data['track'] = data['name'].split('/')

    problems = th.getProblems(data)

    output = []

    for problem in problems:
        # TODO: Replace 1 with user of hub NOT current user
        modelSummaries = db.ModelSummaries(1, data['hub'], data['track'], problem['ref'], problem['start']).get()

        if len(modelSummaries.index) < 1:
            # TODO: LOPART HERE
            continue

        nonZeroRegions = modelSummaries[modelSummaries['regions'] > 0]

        minError = nonZeroRegions[nonZeroRegions['errors'] == nonZeroRegions['errors'].min()]

        # Uses first penalty with min label error
        # This will favor the model with the lowest penalty, given that summary is sorted
        penalty = minError['penalty'].iloc[0]

        # TODO: Replace 1 with user of hub NOT current user
        minErrorModel = db.Model(1, data['hub'], data['track'], problem['ref'], problem['start'], penalty)

        # TODO: If no good model, do LOPART

        model = loadModelDf(minErrorModel.get(), data)

        output.extend(model)

    return output


def loadModelDf(df, data):
    onlyPeaks = df[df['annotation'] == 'peak']

    inView = onlyPeaks.apply(checkInBounds, axis=1, args=(data, ))

    output = onlyPeaks[inView]

    output.columns = jbrowseModelColumns

    return output.to_dict('records')


def checkInBounds(row, data):
    if not data['ref'] == row['chrom']:
        return False

    startIn = data['start'] <= row['chromStart'] <= data['end']
    endIn = data['start'] >= row['chromEnd'] <= data['end']
    wrap = (row['chromStart'] < data['start']) and (row['chromEnd'] > data['end'])

    return startIn or endIn or wrap


def updateAllModelLabels(data):
    data['hub'], data['track'] = data['name'].split('/')

    # This is the problems that the label update is in
    problems = th.getProblems(data)

    for problem in problems:
        # TODO: Replace 1 with hub user NOT current user
        modelSummaries = db.ModelSummaries(1, data['hub'], data['track'], problem['ref'], problem['start'])
        modelsums = modelSummaries.get()

        if len(modelsums.index) < 1:
            submitPregenJob(problem, data)
            continue

        labelQuery = {'name': data['name'], 'ref': problem['ref'], 'start': problem['start'], 'end': problem['end']}
        labels = pd.DataFrame(th.getLabels(labelQuery))
        if len(labels.index) < 1:
            continue
        labels.columns = labelColumns

        newSum = modelsums.apply(modelSumLabelUpdate, axis=1, args=(labels, data, problem))

        modelSummaries.add(newSum)

        checkGenerateArgs = (modelSummaries, problem, data)
        cgThread = threading.Thread(target=checkGenerateModels, args=checkGenerateArgs, daemon=True)
        cgThread.start()


def modelSumLabelUpdate(modelSum, labels, data, problem):
    # TODO: Replace 1 with hub user unique identifier
    modelob = db.Model(1, data['hub'], data['track'], problem['ref'], problem['start'], modelSum['penalty'])

    modeldf = modelob.get()

    if len(modeldf.index) < 1 > len(labels.index):
        return modeldf

    return calculateModelLabelError(modeldf, labels, modelSum['penalty'])


def checkGenerateModels(modelSums, problem, data):
    sumdf = modelSums.get()

    nonZeroRegions = sumdf[sumdf['regions'] > 0]

    minError = nonZeroRegions[nonZeroRegions['errors'] == nonZeroRegions['errors'].min()]

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
                above = sumdf.iloc[index + 1]
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
                below = sumdf.iloc[index - 1]
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
    trackInfo = modelInfo['trackInfo']
    penalty = data['penalty']

    # TODO: Replace 1 with user of hub NOT current user
    model = db.Model(1, trackInfo['hub'], trackInfo['track'], problem['ref'], problem['start'], penalty)
    modelSummaries = db.ModelSummaries(1, trackInfo['hub'], trackInfo['track'], problem['ref'], problem['start'])

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
        f.writelines(modelData)

        f.flush()
        f.seek(0)

        df = pd.read_csv(f.name, sep='\t', header=None)
        df.columns = modelColumns

        labelQuery = {'name': trackInfo['name'], 'ref': problem['ref'], 'start': problem['start'], 'end': problem['end']}
        labels = pd.DataFrame(th.getLabels(labelQuery))
        labels.columns = labelColumns

        errorSum = calculateModelLabelError(df, labels, penalty)

        model.put(df)

        if errorSum is None:
            return

        modelSummaries.add(errorSum)
    return modelInfo


def calculateModelLabelError(modelDf, labels, penalty):
    labels = labels[labels['annotation'] != 'unknown']
    peaks = modelDf[modelDf['annotation'] == 'peak']
    errorSeries = pd.Series({'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0,
                          'errors': 0, 'penalty': penalty, 'numPeaks': len(peaks.index)})
    if len(labels.index) < 1 > len(peaks.index):
        return errorSeries

    error = PeakError.error(peaks, labels)
    if error is None:
        return errorSeries

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = len(peaks.index)

    singleRow = summary.iloc[0]

    return singleRow


def getPrePenalties(problem, data):
    genome = data['genome']

    # TODO: Make this actually learn based on previous data

    return [100, 1000, 10000, 100000, 1000000]
