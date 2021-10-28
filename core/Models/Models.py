import LOPART
import FLOPART
import logging
import PeakError
import numpy as np
import pandas as pd
from simpleBDB import retry, txnAbortOnError

log = logging.getLogger(__name__)
from glmnet_python import cvglmnetPredict
from core.util import PLConfig as cfg, PLdb as db, bigWigUtil as bw
from core.Handlers import Tracks
from core.Jobs import Jobs

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
jbrowseModelColumns = ["ref", "start", "end", "type", "score"]
peakSegDiskPrePenalties = [1000, 10000, 100000, 1000000]
flopartLabels = {'noPeak': 0,
                 'noPeaks': 0,
                 'peakStart': 1,
                 'peakEnd': -1,
                 'unknown': -2}
modelTypes = ['lopart', 'flopart']
pd.set_option('mode.chained_assignment', None)


@retry
@txnAbortOnError
def getModels(data, txn=None):
    chromLabels = db.Labels(data['user'], data['hub'], data['track'], data['ref']).get(txn=txn)

    problems = Tracks.getProblems(data, txn=txn)

    output = pd.DataFrame()

    for problem in problems:
        isInBounds = chromLabels.apply(db.checkInBounds, axis=1,
                                       args=(problem['chrom'], problem['chromStart'], problem['chromEnd']))

        problemLabels = chromLabels[isInBounds]

        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart']).get(txn=txn)

        if len(modelSummaries.index) < 1:
            altout = generateAltModel(data, problem, problemLabels, txn=txn)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)

            continue

        if len(modelSummaries.index) == 1:
            sum = modelSummaries.iloc[0]

            # This is probably a predict model then
            if sum['regions'] == 0 and sum['errors'] != -1:
                if isinstance(sum['penalty'], str):
                    penalty = sum['penalty']
                else:
                    if str(sum['penalty']).split('.')[1] == '0':
                        penalty = '%g' % sum['penalty'].item()
                    else:
                        penalty = str(sum['penalty'])

                minErrorModelDb = db.Model(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart'],
                                           penalty)
                try:
                    minErrorModel = minErrorModelDb.get(txn=txn)
                except KeyError:
                    log.warning('Missing a model for summary', modelSummaries)
                    continue

                minErrorModel = minErrorModel[minErrorModel['annotation'] == 'peak']
                minErrorModel.columns = jbrowseModelColumns

                output = output.append(minErrorModel, ignore_index=True)
                continue
            else:
                altout = generateAltModel(data, problem, problemLabels, txn=txn)
                if isinstance(altout, pd.DataFrame):
                    output = output.append(altout, ignore_index=True)
                continue

        # Remove processing models from ones which can be displayed
        modelSummaries = modelSummaries[modelSummaries['errors'] >= 0]

        if len(modelSummaries.index) < 1:
            altout = generateAltModel(data, problem, problemLabels, txn=txn)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        nonZeroRegions = modelSummaries[modelSummaries['regions'] > 0]

        if len(nonZeroRegions.index) < 1:
            altout = generateAltModel(data, problem, problemLabels, txn=txn)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        withPeaks = nonZeroRegions[nonZeroRegions['numPeaks'] > 0]

        if len(withPeaks.index) < 1:
            altout = generateAltModel(data, problem, problemLabels, txn=txn)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        noError = withPeaks[withPeaks['errors'] < 1]

        if len(noError.index) < 1:
            altout = generateAltModel(data, problem, problemLabels, txn=txn)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        elif len(noError.index) > 1:
            # Select which model to display from modelSums with 0 error
            noError = whichModelToDisplay(data, problem, noError)

        penalty = noError['penalty'].iloc[0]

        minErrorModelDb = db.Model(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'],
                                   penalty)
        try:
            minErrorModel = minErrorModelDb.getInBounds(data['ref'], data['start'], data['end'], txn=txn)
        except KeyError:
            log.warning('Missing a model for summary', modelSummaries)
            continue
        minErrorModel = minErrorModel[minErrorModel['annotation'] == 'peak']
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

        output = output.append(model, ignore_index=True)

    if len(output.index) < 1:
        return []

    return output


# Called but using pandas.apply, coverage this isn't picked up in coverage
def whichModelToDisplay(data, problem, summary):  # pragma: no cover
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

        problemKey = (data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'])

        modelSummaries = db.ModelSummaries(*problemKey)

        modelsums = modelSummaries.get(txn=modelTxn, write=True)

        if len(modelsums.index) < 1:
            out = Jobs.PregenJob(data['user'],
                                 data['hub'],
                                 data['track'],
                                 problem,
                                 peakSegDiskPrePenalties,
                                 len(labels.index))

            out.putNewJob(txn=modelTxn)
            placeHolders = out.getJobModelSumPlaceholder()
            modelSummaries.put(placeHolders, txn=modelTxn)
            modelTxn.commit()
            continue

        newSum = modelsums.apply(modelSumLabelUpdate, axis=1, args=(labels, data, problem, modelTxn))

        try:
            toDelete = newSum['delete'] == 1
            newSum = newSum[~toDelete].drop('delete', axis=1)
        except KeyError:
            pass

        modelSummaries.put(newSum, txn=modelTxn)

        modelTxn.commit()


def modelSumLabelUpdate(modelSum, labels, data, problem, txn):
    modelDb = db.Model(data['user'], data['hub'], data['track'], problem['chrom'],
                       problem['chromStart'], modelSum['penalty'])

    model = modelDb.get(txn=txn)

    if model is None:
        modelSum['delete'] = True
        return modelSum
    elif model.empty:
        modelSum['delete'] = True
        modelDb.put(None, txn=txn)
        return modelSum

    return calculateModelLabelError(model, labels, problem, modelSum['penalty'])


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
    labels = db.Labels(user, hub, track, problem['chrom']).getInBounds(problem['chrom'],
                                                                       problem['chromStart'],
                                                                       problem['chromEnd'], txn=txn)

    modelSumsDb = db.ModelSummaries(user, hub, track, problem['chrom'], problem['chromStart'])

    if len(labels.index) > 0:
        errorSum = calculateModelLabelError(modelData, labels, problem, penalty)
        modelSumsDb.add(errorSum, txn=txn)
    else:
        peaks = modelData[modelData['annotation'] == 'peak']
        errorSum = getErrorSeries(penalty, len(peaks.index), errors=0)
        modelSumsDb.add(errorSum, txn=txn)

    return modelInfo


def calculateModelLabelError(modelDf, labels, problem, penalty):
    peaks = modelDf[modelDf['annotation'] == 'peak']
    numPeaks = len(peaks.index)
    if not labels.empty:
        labels = labels[labels['annotation'] != 'unknown']
        labelsIsInProblem = labels.apply(db.checkInBounds, axis=1,
                                         args=(problem['chrom'], problem['chromStart'], problem['chromEnd']))
        labelsInProblem = labels[labelsIsInProblem]

        numLabelsInProblem = len(labelsInProblem.index)
    else:
        return getErrorSeries(penalty, numPeaks, 0,
                              errors=0,
                              fn=0,
                              possible_fn=0,
                              fp=0,
                              possible_fp=0)

    if numPeaks <= 0 < numLabelsInProblem:
        noPeaks = labelsInProblem['annotation'] == 'noPeaks'
        noPeak = labelsInProblem['annotation'] == 'noPeak'
        noPeaksBool = noPeak | noPeaks

        noPeaksDf = labelsInProblem[noPeaksBool]

        noPeakLabels = len(noPeaksDf.index)

        errors = numLabelsInProblem - noPeakLabels

        return getErrorSeries(penalty, numPeaks, numLabelsInProblem,
                              errors=errors,
                              fn=errors,
                              possible_fn=errors,
                              fp=0,
                              possible_fp=numLabelsInProblem)

    if numLabelsInProblem < 1:
        return getErrorSeries(penalty, numPeaks, numLabelsInProblem)

    error = PeakError.error(peaks, labelsInProblem)

    if error is None:
        return getErrorSeries(penalty, numPeaks, numLabelsInProblem)

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = numPeaks

    singleRow = summary.iloc[0]

    return singleRow


def getErrorSeries(penalty, numPeaks, regions=0, errors=-1, fp=0, possible_fp=0, fn=0, possible_fn=0):
    return pd.Series({'regions': regions, 'fp': fp, 'possible_fp': possible_fp, 'fn': fn, 'possible_fn': possible_fn,
                      'errors': errors, 'penalty': penalty, 'numPeaks': numPeaks})


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


def getZoomIn(problem):
    return {'start': problem['chromStart'],
            'end': problem['chromEnd'],
            'ref': problem['chrom'],
            'score': 0,
            'type': 'zoomIn'}


def generateAltModel(data, problem, labels, txn=None):
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

    hubInfo = db.HubInfo(user, hub).get(txn=txn)
    trackUrl = hubInfo['tracks'][data['track']]['url']

    start = max(data['visibleStart'], problem['chromStart'], 0)
    end = min(data['visibleEnd'], problem['chromEnd'])

    scaledBins = int(scale * (end - start))

    if scaledBins <= 0:
        return []

    lenBin = (end - start) / scaledBins

    denom = end - start

    inBoundsLabels = labels.apply(db.checkInBounds, axis=1, args=(chrom, start, end))
    labels = labels[inBoundsLabels]

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

    if len(labelsToUse.index) > 1:
        prevEnd = None

        newLabels = pd.DataFrame()

        for index, row in labelsToUse.iterrows():

            if prevEnd is None:
                pass
            elif prevEnd == row['start']:
                row['start'] += 1

            prevEnd = row['end']

            newLabels = newLabels.append(row, ignore_index=True)

        labelsToUse = newLabels

        sameStartEnd = (labelsToUse['end'] - labelsToUse['start']) <= 1

        if sameStartEnd.any():
            return pd.DataFrame([getZoomIn(problem)])

    # TODO: Cache this
    sumData = bw.bigWigSummary(trackUrl, chrom, start, end, scaledBins)

    if len(sumData) < 1:
        log.warning('Sum Data is 0 for alt model', data)
        return []

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

    output = []

    peakPrev = None
    currentPeak = pd.DataFrame()
    for index, row in flopartOut.iterrows():
        if row['state'] != 0:
            currentPeak = currentPeak.append(row, ignore_index=True)

        # Prev data point is the end of a peak
        else:
            if len(currentPeak.index) != 0:
                output.append(maxJumpOnPeaks(currentPeak, peakPrev))

                currentPeak = pd.DataFrame()

            peakPrev = row

    # Handles the case where the model ends with a peak
    if len(currentPeak.index) > 0:
        output.append(maxJumpOnPeaks(currentPeak, peakPrev))

    return pd.concat(output, axis=1).T


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


# This block of code is ran but coverage doesn't pick it up as
def convertLabelsToIndexBased(row, modelStart, denom, bins, modelType):  # pragma: no cover
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
            log.warning('unknownAnnotation', output['annotation'])
            output['change'] = -2

    return output


def doPrediction(job, txn=None):
    features = db.Features(job.user,
                           job.hub,
                           job.track,
                           job.problem['chrom'],
                           job.problem['chromStart']).get(txn=txn)

    if not isinstance(features, pd.Series):
        if not features:
            return False

    model = db.Prediction('model').get(txn=txn)

    if not isinstance(model, dict):
        return False

    colsToDrop = db.Prediction('badCols').get(txn=txn)

    featuresDropped = features.drop(labels=colsToDrop)

    prediction = predictWithFeatures(featuresDropped, model)

    if prediction is None:
        return False

    return float(10 ** prediction)


def predictWithFeatures(features, model):
    if not isinstance(features, pd.Series):
        raise Exception(features)

    featuresDf = pd.DataFrame().append(features, ignore_index=True)
    guess = cvglmnetPredict(model, newx=featuresDf, s='lambda_min')[0][0]

    if np.isnan(guess):
        return

    return guess

def profile_wrap(func):
    import cProfile

    def wrap(*args, **kwargs):
        with cProfile.Profile() as pr:
            output = func(*args, **kwargs)

        pr.print_stats(sort='filename')
        return output

    return wrap


@retry
@txnAbortOnError
def getTrackModelSummaries(data, txn=None):
    problems = Tracks.getProblems(data, txn=txn)

    output = []

    for problem in problems:
        problemTxn = db.getTxn(parent=txn)

        modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                           problem['chromStart']).get(txn=problemTxn)

        problemTxn.commit()

        if len(modelSummaries.index) < 1:
            continue

        output.append({'problem': problem, 'htmlData': modelSummaries.to_html()})

    return output


@retry
@txnAbortOnError
def getTrackModelSummary(data, txn=None):
    hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)

    problems = db.Problems(hubInfo['genome']).get(txn=txn)

    sameChrom = problems[problems['chrom'] == data['ref']]

    sameStart = sameChrom[sameChrom['chromStart'] == data['start']]

    if len(sameStart) != 1:
        return

    problem = sameStart.iloc[0]

    modelSummaries = db.ModelSummaries(data['user'], data['hub'], data['track'], problem['chrom'],
                                       problem['chromStart']).get(txn=txn)

    return modelSummaries


@retry
@txnAbortOnError
def recalculateModels(data, txn=None):
    modelSumCursor = db.ModelSummaries.getCursor(txn=txn, bulk=True)

    current = modelSumCursor.next()

    genomes = {}

    while current is not None:
        key, modelSum = current

        modelSum = modelSum[modelSum['errors'] >= 0]

        if not modelSum['penalty'].is_unique:
            modelSum = modelSum.drop_duplicates()
            if not modelSum['penalty'].is_unique:
                print(modelSum)
                break

        user, hub, track, ref, start = key

        hubInfo = db.HubInfo(user, hub).get(txn=txn)

        genome = hubInfo['genome']

        if not genome in genomes:
            problems = db.Problems(genome).get(txn=txn)

            genomes[genome] = problems
        else:
            problems = genomes[genome]

        chromProblems = problems[problems['chrom'] == ref]

        problem = chromProblems[chromProblems['chromStart'] == int(start)].iloc[0]

        labels = db.Labels(user, hub, track, ref).get(txn=txn)

        sumData = {'user': user, 'hub': hub, 'track': track, **problem.to_dict()}

        newSum = modelSum.apply(modelSumLabelUpdate, axis=1, args=(labels, sumData, sumData, txn)).reset_index(drop=True)

        try:
            toDelete = newSum['delete'] == 1
            newSum = newSum[~toDelete].drop('delete', axis=1)
        except KeyError:
            pass

        modelSumCursor.put(key, newSum)

        current = modelSumCursor.next()

    modelSumCursor.close()


@retry
@txnAbortOnError
def fixModelsToModelSums(data, txn=None):
    modelKeys = db.Model.db_key_tuples()

    organizedKeys = {}

    for key in modelKeys:
        recursiveCheck(organizedKeys, list(key))

    for user, hubs in organizedKeys.items():
        for hub, tracks in hubs.items():
            hubInfo = db.HubInfo(user, hub).get(txn=txn)
            genome = hubInfo['genome']
            problems = db.Problems(genome).get(txn=txn)
            for track, chroms in tracks.items():
                for chrom, starts in chroms.items():
                    chromProblems = problems[problems['chrom'] == chrom]
                    labels = db.Labels(user, hub, track, chrom).get(txn=txn)
                    for start, penalties in starts.items():
                        sumDb = db.ModelSummaries(user, hub, track, chrom, start)
                        modelSumTxn = db.getTxn(parent=txn)
                        modelSums = sumDb.get(txn=modelSumTxn, write=True)
                        start = int(start)
                        problem = chromProblems[chromProblems['chromStart'] == start].iloc[0]
                        notInSum = []

                        for penalty in penalties:
                            if (modelSums['penalty'] == float(penalty)).any():
                                continue
                            else:
                                modelDb = db.Model(user, hub, track, chrom, start, penalty)
                                if float(penalty) <= 0:
                                    modelDb.put(None, txn=modelSumTxn)
                                    continue

                                model = modelDb.get(txn=modelSumTxn)

                                if model is None:
                                    print('model is none')
                                    modelSumTxn.abort()
                                    raise Exception
                                elif model.empty:
                                    print('model is empty')
                                    modelSumTxn.abort()
                                    raise Exception

                                notInSum.append(calculateModelLabelError(model, labels, problem, penalty))

                        if len(notInSum) > 0:
                            notInSums = pd.DataFrame(notInSum)
                            sumDb.put(notInSums, txn=modelSumTxn)
                            modelSumTxn.commit()
                        else:
                            modelSumTxn.abort()


def recursiveCheck(data, key):
    toCheck = key[0]
    if toCheck not in data:
        if len(key) <= 2:
            data[toCheck] = [key[1]]
            return

        data[toCheck] = {}
        key = key[1:]
        return recursiveCheck(data[toCheck], key)

    else:
        if len(key) <= 2:
            try:
                data[toCheck].append(key[1])
            except AttributeError:
                print(data)

                print(toCheck)
                raise
            return

        key = key[1:]
        return recursiveCheck(data[toCheck], key)


if cfg.testing:
    @retry
    @txnAbortOnError
    def modelSumUpload(data, txn=None):
        user = data['user']
        hub = data['hub']
        track = data['track']
        problem = data['problem']

        sum = pd.read_json(data['sum'])

        sumsDb = db.ModelSummaries(user, hub, track, problem['chrom'], problem['chromStart'])

        sumsDb.add(sum, txn=txn)
