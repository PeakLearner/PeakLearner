import PeakError
import LOPART
import subprocess
import pandas as pd
import numpy as np
from api.util import PLConfig as pl, PLdb as db, bigWigUtil as bw
from api.Handlers import Labels, Jobs, Tracks, Handler

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
jbrowseModelColumns = ["ref", "start", "end", "type", "score"]


class ModelHandler(Handler.TrackHandler):
    """Handles Label Commands"""
    key = 'models'

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        return {'get': getModels,
                'getModelSummary': getModelSummary,
                'put': putModel}


def getModels(data):
    problems = Tracks.getProblems(data)

    output = []

    for problem in problems:
        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart']).get()
        if len(modelSummaries.index) < 1:
            lopartOutput = generateLOPARTModel(data, problem)
            output.extend(lopartOutput)
            continue

        nonZeroRegions = modelSummaries[modelSummaries['regions'] > 0]

        if len(nonZeroRegions.index) < 1:
            lopartOutput = generateLOPARTModel(data, problem)
            output.extend(lopartOutput)
            continue

        noError = nonZeroRegions[nonZeroRegions['errors'] < 1]

        if len(noError.index) < 1:
            lopartOutput = generateLOPARTModel(data, problem)
            output.extend(lopartOutput)
            continue

        elif len(noError.index) > 1:
            # Uses highest penalty with 0 label error
            # This will result in underfitting
            # TODO: make model choice a function
            noError = noError[noError['numPeaks'] == noError['numPeaks'].min()]

        # Uses first penalty with min label error
        # This will favor the model with the lowest penalty, given that summary is sorted
        penalty = noError['penalty'].iloc[0]

        minErrorModel = db.Model(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'],
                                 penalty)

        model = minErrorModel.getInBounds(data['ref'], data['start'], data['end'])
        onlyPeaks = model[model['annotation'] == 'peak']
        # Organize the columns
        onlyPeaks = onlyPeaks[modelColumns]
        onlyPeaks.columns = jbrowseModelColumns
        print(onlyPeaks.to_dict('records'))
        output.extend(onlyPeaks.to_dict('records'))
    return output


def updateAllModelLabels(data, labels):
    # This is the problems that the label update is in
    problems = Tracks.getProblems(data)

    for problem in problems:
        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart'])
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
    model = db.Model(data['user'], data['hub'], data['track'], problem['chrom'],
                     problem['chromStart'], modelSum['penalty']).get(txn=txn)

    return calculateModelLabelError(model, labels, problem, modelSum['penalty'])


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
    Jobs.updateJob(job)


def submitPregenJob(problem, data):
    penalties = getPrePenalties(problem, data)
    job = {'numModels': len(penalties),
           'user': data['user'],
           'hub': data['hub'],
           'track': data['track'],
           'jobType': 'pregen',
           'jobData': {'problem': problem, 'penalties': penalties}}
    Jobs.updateJob(job)


def submitGridSearch(problem, data, minPenalty, maxPenalty, num=pl.gridSearchSize):
    job = {'numModels': num,
           'user': data['user'],
           'hub': data['hub'],
           'track': data['track'],
           'jobType': 'gridSearch',
           'jobData': {'problem': problem, 'minPenalty': float(minPenalty), 'maxPenalty': float(maxPenalty)}}

    Jobs.updateJob(job)


def putModel(data):
    modelData = pd.read_json(data['modelData'])
    modelData.columns = modelColumns
    modelInfo = data['modelInfo']
    problem = modelInfo['problem']
    penalty = data['penalty']
    user = modelInfo['user']
    hub = modelInfo['hub']
    track = modelInfo['track']

    txn = db.getTxn()
    db.Model(user, hub, track, problem['chrom'], problem['chromStart'], penalty).put(modelData, txn=txn)
    labels = db.Labels(user, hub, track, problem['chrom']).get(txn=txn)
    errorSum = calculateModelLabelError(modelData, labels, problem, penalty)
    db.ModelSummaries(user, hub, track, problem['chrom'], problem['chromStart']).add(errorSum, txn=txn)
    txn.commit()

    return modelInfo


def calculateModelLabelError(modelDf, labels, problem, penalty):
    labels = labels[labels['annotation'] != 'unknown']
    peaks = modelDf[modelDf['annotation'] == 'peak']
    numPeaks = len(peaks.index)

    if len(labels.index) < 1 > numPeaks:
        return getErrorSeries(penalty, numPeaks)

    labelsIsInProblem = labels.apply(db.checkInBounds, axis=1,
                                     args=(problem['chrom'], problem['chromStart'], problem['chromEnd']))

    labelsInProblem = labels[labelsIsInProblem]

    if len(labels.index) < 1:
        return getErrorSeries(penalty, numPeaks)

    error = PeakError.error(peaks, labelsInProblem)

    if error is None:
        return getErrorSeries(penalty, numPeaks)

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = numPeaks

    singleRow = summary.iloc[0]

    return singleRow


def getModelSummary(data):
    problems = Tracks.getProblems(data)

    output = {}

    for problem in problems:
        # TODO: Replace 1 with user of hub NOT current user
        modelSummaries = db.ModelSummaries(1, data['hub'], data['track'], problem['chrom'], problem['chromStart']).get()

        if len(modelSummaries.index) < 1:
            continue

        output[problem['chromStart']] = modelSummaries.to_dict('records')

    return output


def getErrorSeries(penalty, numPeaks):
    return pd.Series({'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0,
                      'errors': 0, 'penalty': penalty, 'numPeaks': numPeaks})


def getPrePenalties(problem, data):
    genome = data['genome']

    # TODO: Make this actually learn based on previous data

    return [1000, 10000, 100000, 1000000]


# TODO: This could be better (learning a penalty based on PeakSegDisk Models?)
def getLOPARTPenalty(data):
    tempPenalties = {0.005: 2000, 0.02: 5000, 0.1: 10000}
    try:
        return tempPenalties[data['scale']]
    except KeyError:
        return 5000


def generateLOPARTModel(data, problem):
    user = data['user']
    hub = data['hub']
    track = data['track']
    chrom = data['ref']
    start = data['start']
    end = data['end']
    hubInfo = db.HubInfo(user, hub).get()
    trackUrl = hubInfo['tracks'][data['track']]['url']
    bins = data['width']

    if not db.checkInBounds(problem, chrom, start, end):
        return

    sumData = bw.bigWigSummary(trackUrl, chrom, start, end, bins)

    dbLabels = db.Labels(user, hub, track, chrom)
    labels = dbLabels.getInBounds(chrom, start, end)
    denom = end - start

    if len(labels.index) < 1:
        labelsToUse = pd.DataFrame({'start': [1], 'end': [2], 'change': [-1]})
    else:
        lopartLabels = labels[(labels['annotation'] != 'unknown') & (labels['annotation'] != 'peak')]

        if len(lopartLabels.index) < 1:
            labelsToUse = pd.DataFrame({'start': [1], 'end': [2], 'change': [-1]})
        else:
            labelsToUse = labels.apply(ConvertLabelsToLopart, axis=1, args=(start, end, denom, bins))

    lopartOut = LOPART.runSlimLOPART(sumData, labelsToUse, getLOPARTPenalty(data))

    if len(lopartOut.index) <= 0:
        return []

    lopartOut['ref'] = chrom

    output = []

    prev = None
    justStarted = False
    for index, row in lopartOut.iterrows():
        if prev is None:
            prev = row
            justStarted = True
            continue
        if justStarted:
            justStarted = False
            if prev['height'] > row['height']:
                output.append({'ref': prev['ref'],
                               'start': prev['start'],
                               'end': prev['end'],
                               'score': prev['height'],
                               'type': 'lopart'})
        if prev['height'] < row['height']:
            output.append({'ref': row['ref'],
                           'start': row['start'],
                           'end': row['end'],
                           'score': row['height'],
                           'type': 'lopart'})

        prev = row

    return output


def ConvertLabelsToLopart(row, modelStart, modelEnd, denom, bins):
    scaledStart = round(((row['chromStart'] - modelStart) * bins) / denom)
    scaledEnd = round(((row['chromEnd'] - modelStart) * bins) / denom)
    if scaledStart <= 1:
        scaledStart = 1
    row['start'] = scaledStart
    if scaledEnd > bins:
        scaledEnd = bins
    row['end'] = scaledEnd

    if row['annotation'] == 'peakStart' or row['annotation'] == 'peakEnd':
        row['change'] = 1
    else:
        row['change'] = 0
    return row
