import PeakError
import pandas as pd
from api import PLdb as db, PLConfig as pl
from api.Handlers import LabelHandler as lh, JobHandler as jh

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
jbrowseModelColumns = ["ref", "start", "end", "type", "score"]


def getModels(data):
    data['hub'], data['track'] = data['name'].split('/')

    problems = lh.getProblems(data)

    output = []

    for problem in problems:
        # TODO: Replace 1 with user of hub NOT current user
        modelSummaries = db.ModelSummaries(1, data['hub'], data['track'], problem['ref'], problem['start']).get()

        if len(modelSummaries.index) < 1:
            # TODO: DEFAULT LOPART HERE
            continue

        nonZeroRegions = modelSummaries[modelSummaries['regions'] > 0]

        if len(nonZeroRegions.index) < 1:
            # TODO: DEFAULT LOPART HERE
            continue

        noError = nonZeroRegions[nonZeroRegions['errors'] < 1]

        if len(noError.index) < 1:
            #TODO: LOPART HERE
            continue

        # Uses first penalty with min label error
        # This will favor the model with the lowest penalty, given that summary is sorted
        penalty = noError['penalty'].iloc[0]


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

    startIn = (data['start'] <= row['chromStart'] <= data['end'])
    endIn = (data['start'] <= row['chromEnd'] <= data['end'])
    wrap = (row['chromStart'] < data['start']) and (row['chromEnd'] > data['end'])

    return startIn or endIn or wrap


def updateAllModelLabels(data, labels):
    data['hub'], data['track'] = data['name'].split('/')
    # Replace user with hub user
    data['user'] = 1

    # This is the problems that the label update is in
    problems = lh.getProblems(data)

    for problem in problems:
        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['ref'], problem['start'])
        modelsums = modelSummaries.get()

        if len(modelsums.index) < 1:
            submitPregenJob(problem, data)
            continue

        txn = db.getTxn()

        newSum = modelsums.apply(modelSumLabelUpdate, axis=1, args=(labels, data, problem, txn))

        item, after = modelSummaries.add(newSum, txn=txn)
        checkGenerateModels(after, problem, data)

        txn.commit()


def modelSumLabelUpdate(modelSum, labels, data, problem, txn):
    model = db.Model(data['user'], data['hub'], data['track'],
                     problem['ref'], problem['start'], modelSum['penalty']).get(txn=txn)

    return calculateModelLabelError(model, labels, modelSum['penalty'])


def checkGenerateModels(modelSums, problem, data):

    nonZeroRegions = modelSums[modelSums['regions'] > 0]

    if len(nonZeroRegions.index) == 0:
        return

    minError = nonZeroRegions[nonZeroRegions['errors'] == nonZeroRegions['errors'].min()]

    if len(minError.index) == 0:
        return

    if minError.iloc[0]['errors'] == 0:
        return

    if len(minError.index) > 1:
        # no need to generate new models if error is 0
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

    elif len(minError.index) == 1:
        index = minError.index[0]

        model = minError.iloc[0]
        if model['fp'] > model['fn']:
            try:
                above = modelSums.iloc[index + 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '*')
                return

            minPenalty = model['penalty']

            maxPenalty = above['penalty']

            # If the next model only has 1 more peak, not worth searching
            if model['numPeaks'] <= above['numPeaks'] + 1:
                return
        else:

            try:
                below = modelSums.iloc[index - 1]
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

    submitPregenJob(problem, data)


def submitOOMJob(problem, data, penalty, jobType):
    job = {'numModels': 1,
           'user': data['user'],
           'hub': data['hub'],
           'track': data['track'],
           'jobType': 'model',
           'jobData': {'problem': problem}}

    if jobType == '*':
        job['jobData']['penalty'] = float(penalty) * 10
    elif jobType == '/':
        job['jobData']['penalty'] = float(penalty) / 10
    else:
        print("Invalid OOM Job")
        return
    jh.updateJob(job)


def submitPregenJob(problem, data):
    penalties = getPrePenalties(problem, data)
    job = {'numModels': len(penalties),
           'user': data['user'],
           'hub': data['hub'],
           'track': data['track'],
           'jobType': 'pregen',
           'jobData': {'problem': problem, 'penalties': penalties}}
    jh.updateJob(job)


def submitGridSearch(problem, data, minPenalty, maxPenalty, num=pl.gridSearchSize):
    job = {'numModels': num,
           'user': data['user'],
           'hub': data['hub'],
           'track': data['track'],
           'jobType': 'gridSearch',
           'jobData': {'problem': problem, 'minPenalty': float(minPenalty), 'maxPenalty': float(maxPenalty)}}

    jh.updateJob(job)


def putModel(data):
    modelData = pd.read_json(data['modelData'])
    modelData.columns = modelColumns
    modelInfo = data['modelInfo']
    problem = modelInfo['problem']
    penalty = data['penalty']
    user = modelInfo['user']
    hub = modelInfo['hub']
    track = modelInfo['track']

    db.Model(user, hub, track, problem['ref'], problem['start'], penalty).put(modelData)
    txn = db.getTxn()
    labels = db.Labels(user, hub, track, problem['ref']).get(txn=txn)
    errorSum = calculateModelLabelError(modelData, labels, penalty)
    if errorSum is None:
        txn.commit()
        raise Exception

    db.ModelSummaries(user, hub, track, problem['ref'], problem['start']).add(errorSum, txn=txn)
    txn.commit()

    return modelInfo


def calculateModelLabelError(modelDf, labels, penalty):
    labels = labels[labels['annotation'] != 'unknown']
    peaks = modelDf[modelDf['annotation'] == 'peak']
    numPeaks = len(peaks.index)

    if len(labels.index) < 1 > numPeaks:
        return getErrorSeries(penalty, numPeaks)

    error = PeakError.error(peaks, labels)

    if error is None:
        return getErrorSeries(penalty, numPeaks)

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = numPeaks

    singleRow = summary.iloc[0]

    return singleRow


def getModelSummary(data):
    problems = lh.getProblems(data)

    output = {}

    for problem in problems:
        # TODO: Replace 1 with user of hub NOT current user
        modelSummaries = db.ModelSummaries(1, data['hub'], data['track'], problem['ref'], problem['start']).get()

        if len(modelSummaries.index) < 1:
            continue

        output[problem['start']] = modelSummaries.to_dict('records')

    return output


def getErrorSeries(penalty, numPeaks):
    return pd.Series({'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0,
                             'errors': 0, 'penalty': penalty, 'numPeaks': numPeaks})


def getPrePenalties(problem, data):
    genome = data['genome']

    # TODO: Make this actually learn based on previous data

    return [100, 1000, 10000, 100000, 1000000]
