import LOPART
import FLOPART
import logging
import PeakError
import numpy as np
import pandas as pd
from simpleBDB import retry, txnAbortOnError

log = logging.getLogger(__name__)
from glmnet_python import cvglmnetPredict
from core.util import PLConfig as pl, PLdb as db, bigWigUtil as bw
from core.Handlers import Tracks
from core.Jobs import Jobs

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
jbrowseModelColumns = ["ref", "start", "end", "type", "score"]
flopartLabels = {'noPeak': 0,
                 'peakStart': 1,
                 'peakEnd': -1,
                 'unknown': -2}
modelTypes = ['lopart', 'flopart']
pd.set_option('mode.chained_assignment', None)


@retry
@txnAbortOnError
def getModels(data, txn=None):
    problems = Tracks.getProblems(data, txn=txn)

    output = pd.DataFrame()

    for problem in problems:
        problemTxn = db.getTxn(parent=txn)

        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart']).get(txn=problemTxn)

        problemTxn.commit()

        if len(modelSummaries.index) < 1:
            altout = generateAltModel(data, problem)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
                print('getModels Output\n', output)
            continue

        nonZeroRegions = modelSummaries[modelSummaries['regions'] > 0]

        if len(nonZeroRegions.index) < 1:
            altout = generateAltModel(data, problem)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        withPeaks = nonZeroRegions[nonZeroRegions['numPeaks'] > 0]

        if len(withPeaks.index) < 1:
            altout = generateAltModel(data, problem)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        noError = withPeaks[withPeaks['errors'] < 1]

        if len(noError.index) < 1:
            altout = generateAltModel(data, problem)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        elif len(noError.index) > 1:
            # Select which model to display from modelSums with 0 error
            noError = whichModelToDisplay(data, problem, noError)

        penalty = noError['penalty'].iloc[0]

        minErrorModelDb = db.Model(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'],
                                   penalty)
        minErrorModel = minErrorModelDb.getInBounds(data['ref'], data['start'], data['end'])
        minErrorModel.columns = jbrowseModelColumns
        output = output.append(minErrorModel, ignore_index=True)

    outlen = len(output.index)

    if outlen == 1:
        return output
    elif outlen > 1:
        return output.sort_values('start', ignore_index=True)
    else:
        return []


@retry
@txnAbortOnError
def getHubModels(data, txn=None):
    modelSumKeys = db.ModelSummaries.keysWhichMatch(data['user'], data['hub'])

    output = pd.DataFrame()

    for key in modelSumKeys:
        user, hub, track, ref, start = key
        currentSum = db.ModelSummaries(*key).get(txn=txn)

        whichModel = noPredictGuess(currentSum)

        if len(whichModel.index) > 1:
            whichModel = whichModel[whichModel['penalty'] == whichModel['penalty'].min()]

        penalty = whichModel['penalty'].values[0]

        model = db.Model(user, hub, track, ref, start, penalty).get(txn=txn)

        model['track'] = track
        model['penalty'] = penalty

        print(model)

        output = output.append(model, ignore_index=True)

    if len(output.index) < 1:
        return []

    return output


def whichModelToDisplay(data, problem, summary):
    try:
        prediction = doPrediction(data, problem)

        # If no prediction, use traditional system
        if prediction is None or prediction is False:
            prediction = noPredictGuess(summary)

        logPenalties = np.log10(summary['penalty'].astype(float))

        compared = abs(prediction - logPenalties)

        toDisplay = compared[compared == compared.min()]

        toDisplayIndex = toDisplay.index[0]

        return pd.DataFrame([summary.iloc[toDisplayIndex]])
    except:
        # This could be better and I could work out the errors more,
        # or I can just use the old reliable method whenever it fails and move on with my life.
        return noPredictGuess(summary)


def noPredictGuess(summary):
    return summary[summary['numPeaks'] == summary['numPeaks'].min()]


def updateAllModelLabels(data, labels, txn):
    # This is the problems that the label update is in

    problems = Tracks.getProblems(data)

    for problem in problems:
        modelTxn = db.getTxn(parent=txn)

        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart'])

        modelsums = modelSummaries.get(txn=modelTxn, write=True)

        if len(modelsums.index) < 1:
            out = submitPregenJob(problem, data, len(labels.index), txn=modelTxn)
            if out is not None:
                modelTxn.commit()
            else:
                modelTxn.abort()
            continue

        newSum = modelsums.apply(modelSumLabelUpdate, axis=1, args=(labels, data, problem, modelTxn))

        modelSummaries.put(newSum, txn=modelTxn)

        checkGenerateModels(newSum, problem, data, txn=modelTxn)

        modelTxn.commit()


def modelSumLabelUpdate(modelSum, labels, data, problem, txn):
    model = db.Model(data['user'], data['hub'], data['track'], problem['chrom'],
                     problem['chromStart'], modelSum['penalty']).get(txn=txn)

    return calculateModelLabelError(model, labels, problem, modelSum['penalty'])


def checkGenerateModels(modelSums, problem, data, txn=None):
    nonZeroLabels = modelSums[modelSums['regions'] > 0]

    if len(nonZeroLabels.index) == 0:
        return False

    nonZeroRegions = nonZeroLabels[nonZeroLabels['numPeaks'] > 0]

    if len(nonZeroRegions.index) == 0:
        return False

    minError = nonZeroRegions[nonZeroRegions['errors'] == nonZeroRegions['errors'].min()]

    numMinErrors = len(minError.index)

    regions = minError['regions'].max()

    if numMinErrors == 0:
        return False

    if minError.iloc[0]['errors'] == 0:
        return False

    if numMinErrors > 1:
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
            submitGridSearch(problem, data, minPenalty, maxPenalty, regions, txn=txn)
            return True
        return False

    elif numMinErrors == 1:
        index = minError.index[0]

        model = minError.iloc[0]
        if model['fp'] > model['fn']:
            try:
                compare = modelSums.iloc[index + 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '*', regions, txn=txn)
                return True

            # If the next model only has 1 more peak, not worth searching
            if model['numPeaks'] <= compare['numPeaks'] + 1:
                return False
        else:

            try:
                compare = modelSums.iloc[index - 1]
            except IndexError:
                submitOOMJob(problem, data, model['penalty'], '/', regions, txn=txn)
                return True

            # If the previous model is only 1 peak away, not worth searching
            if compare['numPeaks'] + 1 >= model['numPeaks']:
                return False

        if compare['penalty'] > model['penalty']:
            top = compare
            bottom = model
        else:
            top = model
            bottom = compare
        submitSearch(data, problem, bottom, top, regions, txn=txn)

        return True

    return True


def submitOOMJob(problem, data, penalty, jobType, regions, txn=None):
    if jobType == '*':
        penalty = float(penalty) * 10
    elif jobType == '/':
        penalty = float(penalty) / 10
    else:
        print("Invalid OOM Job")
        return

    job = Jobs.SingleModelJob(data['user'],
                              data['hub'],
                              data['track'],
                              problem,
                              penalty,
                              regions)

    job.putNewJobWithTxn(txn=txn)


def submitPregenJob(problem, data, regions, txn=None):
    penalties = getPrePenalties()

    job = Jobs.PregenJob(data['user'],
                         data['hub'],
                         data['track'],
                         problem,
                         penalties,
                         regions)

    return job.putNewJobWithTxn(txn=txn)


def submitGridSearch(problem, data, minPenalty, maxPenalty, regions, num=pl.gridSearchSize, txn=None):
    minPenalty = float(minPenalty)
    maxPenalty = float(maxPenalty)
    penalties = np.linspace(minPenalty, maxPenalty, num + 2).tolist()[1:-1]
    if 'trackUrl' in data:
        job = Jobs.GridSearchJob(data['user'],
                                 data['hub'],
                                 data['track'],
                                 problem,
                                 penalties,
                                 regions,
                                 trackUrl=data['trackUrl'])
    else:
        job = Jobs.GridSearchJob(data['user'],
                                 data['hub'],
                                 data['track'],
                                 problem,
                                 penalties,
                                 regions)

    job.putNewJobWithTxn(txn=txn)


def submitSearch(data, problem, bottom, top, regions, txn=None):
    bottomLoss = db.Loss(data['user'],
                         data['hub'],
                         data['track'],
                         problem['chrom'],
                         problem['chromStart'],
                         bottom['penalty']).get()

    topLoss = db.Loss(data['user'],
                      data['hub'],
                      data['track'],
                      problem['chrom'],
                      problem['chromStart'],
                      top['penalty']).get()

    if topLoss is None or bottomLoss is None:
        return

    penalty = abs((topLoss['meanLoss'] - bottomLoss['meanLoss'])
                  / (bottomLoss['peaks'] - topLoss['peaks'])).iloc[0].astype(float)

    print('submitSearch', penalty, type(penalty))

    job = Jobs.SingleModelJob(data['user'],
                              data['hub'],
                              data['track'],
                              problem,
                              penalty,
                              regions)

    job.putNewJobWithTxn(txn=txn)


@retry
@txnAbortOnError
def putModel(data, txn=None):
    modelData = pd.read_json(data['modelData'])
    modelData.columns = modelColumns
    modelInfo = data['modelInfo']
    problem = modelInfo['problem']
    penalty = data['penalty']
    user = modelInfo['user']
    hub = modelInfo['hub']
    track = modelInfo['track']

    db.Model(user, hub, track, problem['chrom'], problem['chromStart'], penalty).put(modelData, txn=txn)
    labels = db.Labels(user, hub, track, problem['chrom']).get(txn=txn)
    db.Prediction('changes').increment(txn=txn)
    errorSum = calculateModelLabelError(modelData, labels, problem, penalty)
    db.ModelSummaries(user, hub, track, problem['chrom'], problem['chromStart']).add(errorSum, txn=txn)
    return modelInfo


def calculateModelLabelError(modelDf, labels, problem, penalty):
    labels = labels[labels['annotation'] != 'unknown']
    peaks = modelDf[modelDf['annotation'] == 'peak']
    numPeaks = len(peaks.index)
    numLabels = len(labels.index)

    if numLabels < 1:
        return getErrorSeries(penalty, numPeaks, numLabels)

    labelsIsInProblem = labels.apply(db.checkInBounds, axis=1,
                                     args=(problem['chrom'], problem['chromStart'], problem['chromEnd']))

    if numPeaks < 1:
        return getErrorSeries(penalty, numPeaks, numLabels)

    labelsInProblem = labels[labelsIsInProblem]

    numLabelsInProblem = len(labelsInProblem.index)

    if numLabelsInProblem < 1:
        return getErrorSeries(penalty, numPeaks, numLabels)

    error = PeakError.error(peaks, labelsInProblem)

    if error is None:
        return getErrorSeries(penalty, numPeaks, numLabels)

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = numPeaks

    singleRow = summary.iloc[0]

    return singleRow


def getModelSummary(data, txn=None):
    problems = Tracks.getProblems(data, txn=txn)

    output = {}

    for problem in problems:
        # TODO: Replace 1 with user of hub NOT current user
        modelSummaries = db.ModelSummaries(data['user'],
                                           data['hub'],
                                           data['track'],
                                           problem['chrom'],
                                           problem['chromStart']).get(txn=txn)

        if len(modelSummaries.index) < 1:
            continue

        output[problem['chromStart']] = modelSummaries.to_dict('records')
    return output


def getErrorSeries(penalty, numPeaks, regions=0):
    return pd.Series({'regions': regions, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0,
                      'errors': 0, 'penalty': penalty, 'numPeaks': numPeaks})


def getPrePenalties():
    return [1000, 10000, 100000, 1000000]


# TODO: This could be better (learning a penalty based on PeakSegDisk Models?)
def getLOPARTPenalty(data):
    tempPenalties = {0.005: 2000, 0.02: 5000, 0.1: 10000}
    try:
        return tempPenalties[data['scale']]
    except KeyError:
        return 5000


# TODO: This could be better (learning a penalty based on PeakSegDisk Models?)
def getFLOPARTPenalty(data):
    tempPenalties = {0.005: 2000, 0.02: 5000, 0.1: 10000}
    try:
        return tempPenalties[data['scale']]
    except KeyError:
        return 5000


def generateAltModel(data, problem):
    if 'modelType' not in data:
        return []

    modelType = data['modelType'].lower()

    if modelType not in modelTypes:
        return []

    user = data['user']
    hub = data['hub']
    track = data['track']
    chrom = data['ref']
    scale = data['scale']
    hubInfo = db.HubInfo(user, hub).get()
    trackUrl = hubInfo['tracks'][data['track']]['url']

    start = max(data['visibleStart'], problem['chromStart'], 0)
    end = min(data['visibleEnd'], problem['chromEnd'])

    scaledBins = int(scale * (end - start))
    lenBin = (end - start) / scaledBins

    # TODO: Cache this
    sumData = bw.bigWigSummary(trackUrl, chrom, start, end, scaledBins)

    if len(sumData) < 1:
        log.warning('Sum Data is 0 for alt model', data)
        return []

    dbLabels = db.Labels(user, hub, track, chrom)
    labels = dbLabels.getInBounds(chrom, start, end)
    denom = end - start

    # either convert labels to an index value or empty dataframe with cols if not
    if len(labels.index) < 1:
        labelsToUse = pd.DataFrame(columns=['start', 'end', 'change'])
    else:
        noUnknowns = labels[labels['annotation'] != 'unknown']

        if len(noUnknowns.index) < 1:
            labelsToUse = pd.DataFrame(columns=['start', 'end', 'change'])
        else:
            labelsToUse = noUnknowns.apply(convertLabelsToIndexBased, axis=1,
                                           args=(start, denom, scaledBins, modelType))

    if modelType == 'lopart':
        out = generateLopartModel(data, sumData, labelsToUse)
    elif modelType == 'flopart':
        out = generateFlopartModel(data, sumData, labelsToUse, lenBin)
    else:
        return []

    if out.empty:
        return []

    # Convert Model output to start ends on the genome
    output = out.apply(indexToStartEnd, axis=1, args=(start, scale)).astype({'start': 'int', 'end': 'int'})

    output['ref'] = chrom
    output['type'] = modelType

    output = output.rename(columns={'height': 'score'})

    return output


def generateLopartModel(data, sumData, labels):
    sumData = sumDataToLopart(sumData)

    out = LOPART.runSlimLOPART(sumData, labels, getLOPARTPenalty(data))

    lopartPeaks = lopartToPeaks(out)

    return lopartPeaks


def sumDataToLopart(data):
    output = []

    for val in data:
        output.append(bw.anscombeApply(val))

    return output


def generateFlopartModel(data, sumData, labels, lenBin):
    sumData = sumDataToFlopart(sumData, lenBin)

    out = FLOPART.runSlimFLOPART(sumData, labels, getFLOPARTPenalty(data))

    return flopartToPeaksUsingMaxJump(out, lenBin)


def sumDataToFlopart(data, lenBin):
    output = []

    for val in data:
        output.append(val * lenBin)

    return output


def lopartToPeaks(lopartOut):
    output = lopartOut.copy()
    output['peak'] = False
    meanHeight = lopartOut['height'].mean()

    prev = None
    for index, row in lopartOut.iterrows():
        if prev is None:
            prev = row
            if row['height'] > meanHeight:
                output['peak'][index] = True
            continue

        if row['height'] > prev['height']:
            output['peak'][index] = True

        prev = row

    peaks = output[output['peak']]

    if peaks.empty:
        return peaks

    peaks['height'] = (peaks['height'] ** 2) - 3 / 8

    return peaks.drop(columns=['peak'])


def flopartToPeaksUsingMaxJump(flopartOut, lenBin):
    flopartOut = flopartOut.rename(columns={'mean': 'height'})

    flopartOut['height'] = (flopartOut['height'] / lenBin)

    output = pd.DataFrame()

    peakPrev = None
    currentPeak = pd.DataFrame()
    for index, row in flopartOut.iterrows():
        if row['state'] != 0:
            currentPeak = currentPeak.append(row)

        # Prev data point is the end of a peak
        else:
            if len(currentPeak.index) != 0:
                output = output.append(maxJumpOnPeaks(currentPeak, peakPrev), ignore_index=True)

                currentPeak = pd.DataFrame()

            peakPrev = row

    # Handles the case where the model ends with a peak
    if len(currentPeak.index) > 0:
        output = output.append(maxJumpOnPeaks(currentPeak, peakPrev), ignore_index=True)

    return output


def maxJumpOnPeaks(currentPeak, peakPrev):
    prev = None

    changes = pd.DataFrame()

    # Calculate changes for
    for curIndex, curRow in currentPeak.iterrows():
        if prev is None:
            if peakPrev is None:
                curRow['change'] = curRow['height']
                changes = changes.append(curRow)
            else:
                curRow['change'] = curRow['height'] - peakPrev['height']
                changes = changes.append(curRow)
            prev = curRow
        else:
            curRow['change'] = curRow['height'] - prev['height']
            changes = changes.append(curRow)

    startRow = changes[changes['change'] == changes['change'].max()]
    endRow = changes[changes['change'] == changes['change'].min()]

    start = startRow['start']
    end = endRow['end']
    height = changes['height'].mean()

    return pd.Series({'start': start, 'end': end, 'height': height})


def indexToStartEnd(row, start, scale):
    row['start'] = round(row['start'] / scale) + start
    row['end'] = round(row['end'] / scale) + start
    return row


def convertLabelsToIndexBased(row, modelStart, denom, bins, modelType):
    scaledStart = round(((row['chromStart'] - modelStart) * bins) / denom)
    scaledEnd = round(((row['chromEnd'] - modelStart) * bins) / denom)

    output = row.copy()
    if scaledStart <= 1:
        scaledStart = 1
    output['start'] = scaledStart
    if scaledEnd > bins:
        scaledEnd = bins
    output['end'] = scaledEnd

    if modelType == 'lopart':
        if output['annotation'] == 'peakStart' or output['annotation'] == 'peakEnd':
            output['change'] = 1
        else:
            output['change'] = 0
    elif modelType == 'flopart':

        # define LABEL_PEAKSTART 1
        # define LABEL_PEAKEND -1
        # define LABEL_UNLABELED -2
        try:
            output['change'] = flopartLabels[output['annotation']]
        except KeyError:
            print('unknownAnnotation', output['annotation'])
            output['change'] = -2

    return output


def doPrediction(data, problem):
    features = db.Features(data['user'],
                           data['hub'],
                           data['track'],
                           problem['chrom'],
                           problem['chromStart']).get()

    if not isinstance(features, pd.Series):
        if not features:
            return False

    model = db.Prediction('model').get()

    if not isinstance(model, dict):
        return False

    colsToDrop = db.Prediction('badCols').get()

    featuresDropped = features.drop(labels=colsToDrop)

    prediction = predictWithFeatures(featuresDropped, model)

    if prediction is None:
        return False
    return prediction


def predictWithFeatures(features, model):
    if not isinstance(features, pd.Series):
        raise Exception(features)

    featuresDf = pd.DataFrame().append(features, ignore_index=True)
    guess = cvglmnetPredict(model, newx=featuresDf, s='lambda_min')[0][0]

    if np.isnan(guess):
        return

    return guess


def numModels():
    return db.Model.length()


def numCorrectModels():
    correct = 0

    for key in db.ModelSummaries.db_key_tuples():
        modelSum = db.ModelSummaries(*key).get()

        if modelSum.empty:
            continue

        withRegions = modelSum[modelSum['regions'] > 0]

        withPeaks = withRegions[withRegions['numPeaks'] > 0]

        zeroErrors = withPeaks[withPeaks['errors'] < 1]

        correct = correct + len(zeroErrors.index)

    return correct
