import os

import pdb

import LOPART
import FLOPART
import logging
import PeakError
import numpy as np
import pandas as pd
import pandas.errors

from core.util import PLConfig as cfg, bigWigUtil as bw
from core.Jobs import Jobs
from core.Prediction import Prediction
from . import PyModels
from core import dbutil, models
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors']
modelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation', 'height']
modelColumnsNoAnnotation = ['chrom', 'chromStart', 'chromEnd', 'height']
jbrowseModelColumns = ['ref', 'start', 'end', 'score']
flopartLabels = {'noPeak': 0,
                 'noPeaks': 0,
                 'peakStart': 1,
                 'peakEnd': -1,
                 'unknown': -2}
modelTypes = ['lopart', 'flopart']
pd.set_option('mode.chained_assignment', None)
modelsPath = os.path.join(cfg.dataPath, 'Models')


def getModels(db: Session,
              authUser,
              user: str,
              hub: str,
              track: str,
              chrom: str,
              start: int,
              end: int,
              modelType: str = 'NONE',
              scale: float = None,
              visibleStart: int = None,
              visibleEnd: int = None):
    chromStr = chrom
    user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, chrom)

    problems = hub.getProblems(db, chrom, start, end)
    output = pd.DataFrame()

    if chrom is not None:
        chromPath = os.path.join(modelsPath, user.name, hub.name, track.name, chrom.name)
        chromLabels = chrom.getLabels(db)
    else:
        chromPath = os.path.join(modelsPath, user.name, hub.name, track.name, chromStr)
        chromLabels = pd.DataFrame()

    for _, problem in problems.iterrows():
        if chrom is None:
            altout = generateAltModel(track,
                                      chromStr,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)

            continue
        contig = chrom.contigs.filter(models.Contig.problem == problem['id']).first()

        if contig is None:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)

            continue

        modelSummaries = contig.getModelSums(db)

        if len(modelSummaries.index) < 1:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)

            continue

        # Remove processing models from ones which can be displayed
        modelSummaries = modelSummaries[modelSummaries['errors'] >= 0]

        if len(modelSummaries.index) < 1:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        # Sums with max regions
        maxRegions = modelSummaries[modelSummaries['regions'] == modelSummaries['regions'].max()]

        if len(maxRegions.index) < 1:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        withPeaks = maxRegions[maxRegions['numPeaks'] > 0]

        if len(withPeaks.index) < 1:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        noError = withPeaks[withPeaks['errors'] < 1]

        if len(noError.index) < 1:
            altout = generateAltModel(track,
                                      chrom.name,
                                      problem,
                                      chromLabels,
                                      modelType=modelType,
                                      scale=scale,
                                      visibleStart=visibleStart,
                                      visibleEnd=visibleEnd)
            if isinstance(altout, pd.DataFrame):
                output = output.append(altout, ignore_index=True)
            continue

        elif len(noError.index) > 1:
            # Select which model to display from modelSums with 0 error
            noError = whichModelToDisplay(db, contig, noError)

        penalty = noError['penalty'].iloc[0]
        modelFilePath = os.path.join(chromPath, str(problem['start']), '%s.bed' % penalty)

        if not os.path.exists(chromPath):
            # Should Alt Model
            raise Exception

        minErrorModel = pd.read_csv(modelFilePath, sep='\t', header=None)
        minErrorModel.columns = jbrowseModelColumns
        output = output.append(minErrorModel, ignore_index=True)

    outlen = len(output.index)

    if outlen == 1:
        return output
    elif outlen > 1:
        return output.sort_values('start', ignore_index=True)
    else:
        return []


def whichModelToDisplay(db, contig, summary):
    try:
        prediction = Prediction.getPenalty(db, contig)

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


def updateAllModelLabels(db: Session, authUser, user, hub, track, chrom, labelsDf, label):
    # This is the problems that the label update is in
    problems = hub.getProblems(db, chrom, label.start, label.end)

    for _, problem in problems.iterrows():
        user, hub, track, chrom, contig, problem = dbutil.getContig(db,
                                                                    user,
                                                                    hub,
                                                                    track,
                                                                    chrom,
                                                                    problem['start'])

        if contig is None:
            # TODO: Pregen job
            continue

        modelSummaries = contig.modelSums.all()

        if len(modelSummaries) < 1:
            # TODO: Pregen Job
            """out = Jobs.PregenJob(data['user'],
                                 data['hub'],
                                 data['track'],
                                 problem,
                                 peakSegDiskPrePenalties,
                                 len(labels.index))"""
            continue

        contigModelsPath = os.path.join(modelsPath, user.name, hub.name, track.name, chrom.name, str(problem.start))

        for modelSum in modelSummaries:
            modelSum = modelSumLabelUpdate(modelSum, labelsDf, problem, contigModelsPath)
            contig.modelSums.append(modelSum)
            db.flush()
            db.refresh(modelSum)
            db.refresh(contig)
        db.commit()


def modelSumLabelUpdate(modelSum, labels, problem, contigModelsPath):
    modelPath = os.path.join(contigModelsPath, '%s.bed' % modelSum.penalty)

    if not os.path.exists(modelPath):
        return modelSum

    try:
        model = pd.read_csv(modelPath, sep='\t', header=None)
        model.columns = modelColumnsNoAnnotation
    except pandas.errors.EmptyDataError:
        model = pd.DataFrame()

    updatedSum = calculateModelLabelError(model, labels, problem, modelSum.penalty)
    modelSum.fp = updatedSum.fp.item()
    modelSum.fn = updatedSum.fn.item()
    modelSum.possible_fp = updatedSum.possible_fp.item()
    modelSum.possible_fn = updatedSum.possible_fn.item()
    modelSum.errors = updatedSum.errors.item()
    modelSum.numPeaks = updatedSum.numPeaks.item()
    modelSum.regions = updatedSum.regions.item()
    return modelSum


def putModel(db, user, hub, track, data: PyModels.ModelData):
    modelData = pd.read_json(data.modelData)
    modelData.columns = modelColumns
    problem = data.problem
    penalty = data.penalty

    contigPath = os.path.join(modelsPath, user, hub, track, problem['chrom'], str(problem['start']))

    if not os.path.exists(contigPath):
        os.makedirs(contigPath)

    modelWithBGFile = '%s_withBG.bed' % penalty

    modelData.to_csv(os.path.join(contigPath, modelWithBGFile), sep='\t', index=False, header=False)

    modelFile = '%s.bed' % penalty

    justPeaks = modelData[modelData.annotation == 'peak']

    toBedGraph = justPeaks.drop('annotation', axis=1)

    toBedGraph.to_csv(os.path.join(contigPath, modelFile), sep='\t', index=False, header=False)

    db.commit()

    user, hub, track, chrom, contig, problem = dbutil.getContig(db,
                                                                user,
                                                                hub,
                                                                track,
                                                                problem['chrom'],
                                                                problem['start'],
                                                                make=True)

    labelsDf = chrom.getLabels(db)

    modelSumOut = calculateModelLabelError(justPeaks, labelsDf, problem, penalty)

    modelSum = models.ModelSum(contig=contig.id,
                               fp=modelSumOut['fp'].item(),
                               fn=modelSumOut['fn'].item(),
                               possible_fp=modelSumOut['possible_fp'].item(),
                               possible_fn=modelSumOut['possible_fn'].item(),
                               errors=modelSumOut['errors'].item(),
                               regions=modelSumOut['regions'].item(),
                               numPeaks=modelSumOut['numPeaks'].item(),
                               loss=pd.read_json(data.lossData),
                               penalty=penalty)

    contig.modelSums.append(modelSum)
    db.commit()
    db.refresh(modelSum)

    return True


def calculateModelLabelError(modelDf, labels, problem, penalty):
    numPeaks = len(modelDf.index)
    if not labels.empty:
        labels = labels[labels['annotation'] != 'unknown']
        try:
            labelsIsInProblem = labels.apply(bw.checkInBounds, axis=1,
                                             args=(problem.start, problem.end))
        except KeyError:
            print(problem)
            print(problem.__dict__)
            raise
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

    elif numLabelsInProblem == 0:
        return getErrorSeries(penalty, numPeaks, numLabelsInProblem, errors=0)

    labelsInProblem = labelsInProblem[['chrom', 'start', 'end', 'annotation']]
    labelsInProblem.columns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
    error = PeakError.error(modelDf, labelsInProblem)

    if error is None:
        return getErrorSeries(penalty, numPeaks, numLabelsInProblem)

    summary = PeakError.summarize(error)
    summary.columns = summaryColumns
    summary['penalty'] = penalty
    summary['numPeaks'] = numPeaks

    singleRow = summary.iloc[0]

    return singleRow


def getErrorSeries(penalty, numPeaks, regions=0, errors=-1, fp=0, possible_fp=0, fn=0, possible_fn=0):
    return pd.Series(
        {'regions': np.int64(regions), 'fp': np.int64(fp), 'possible_fp': np.int64(possible_fp), 'fn': np.int64(fn),
         'possible_fn': np.int64(possible_fn),
         'errors': np.int64(errors), 'penalty': penalty, 'numPeaks': np.int64(numPeaks)})


# TODO: This could be better (learning a penalty based on PeakSegDisk Models?)
def getLOPARTPenalty(scale):
    tempPenalties = {0.005: 2000, 0.02: 5000, 0.1: 10000}
    try:
        return tempPenalties[scale]
    except KeyError:
        return 5000


# TODO: This could be better (learning a penalty based on PeakSegDisk Models?)
def getFLOPARTPenalty(scale):
    tempPenalties = {0.005: 2000, 0.02: 5000, 0.1: 10000}
    try:
        return tempPenalties[scale]
    except KeyError:
        return 5000


def getZoomIn(problem):
    return {'start': problem['chromStart'],
            'end': problem['chromEnd'],
            'ref': problem['chrom'],
            'score': 0,
            'type': 'zoomIn'}


def generateAltModel(track,
                     chrom,
                     problem,
                     labels,
                     modelType: str = 'NONE',
                     scale: float = None,
                     visibleStart: int = None,
                     visibleEnd: int = None):
    if modelType == 'NONE':
        return []

    modelType = modelType.lower()

    if modelType not in modelTypes:
        return []

    trackUrl = track.url

    start = max(visibleStart, problem['start'], 0)
    end = min(visibleEnd, problem['end'])

    scaledBins = int(scale * (end - start))

    if scaledBins <= 0:
        return []

    lenBin = (end - start) / scaledBins

    denom = end - start

    inBoundsLabels = labels.apply(bw.checkInBounds, axis=1, args=(start, end))
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

        labelsToUse = newLabels.sort_values('start', ignore_index=True)

        sameStartEnd = (labelsToUse['end'] - labelsToUse['start']) <= 1

        if sameStartEnd.any():
            return pd.DataFrame([getZoomIn(problem)])

    # TODO: Cache this
    sumData = bw.bigWigSummary(trackUrl, chrom, start, end, scaledBins)

    if len(sumData) < 1:
        return []

    if modelType == 'lopart':
        out = generateLopartModel(scale, sumData, labelsToUse)
    elif modelType == 'flopart':
        out = generateFlopartModel(scale, sumData, labelsToUse, lenBin)
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


def generateLopartModel(scale, sumData, labels):
    sumData = sumDataToLopart(sumData)

    out = LOPART.runSlimLOPART(sumData, labels, getLOPARTPenalty(scale))

    lopartPeaks = lopartToPeaks(out)

    return lopartPeaks


def sumDataToLopart(data):
    output = []

    for val in data:
        output.append(bw.anscombeApply(val))

    return output


def generateFlopartModel(scale, sumData, labels, lenBin):
    sumData = sumDataToFlopart(sumData, lenBin)

    out = FLOPART.runSlimFLOPART(sumData, labels, getFLOPARTPenalty(scale))

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
    scaledStart = round(((row['start'] - modelStart) * bins) / denom)
    scaledEnd = round(((row['end'] - modelStart) * bins) / denom)

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


def getTrackModelSummaries(db: Session, user, hub, track, ref, start, end):
    user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, ref)

    if chrom is None:
        return

    problems = hub.getProblems(db, ref, start, end)

    modelSums = []

    for _, problem in problems.iterrows():
        contig = chrom.contigs.filter(models.Contig.problem == problem['id']).first()

        if contig is None:
            continue

        modelSummaries = contig.getModelSums(db)

        if len(modelSummaries.index) < 1:
            continue

        modelSums.append({'problem': problem, 'htmlData': modelSummaries.to_html()})

    return modelSums


def getTrackModelSummary(db: Session, user, hub, track, ref, start):
    user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, ref)

    if chrom is None:
        return

    problems = hub.getProblems(db, ref, start)

    sameChrom = problems[problems['chrom'] == ref]

    sameStart = sameChrom[sameChrom['chromStart'] == start]

    if len(sameStart) != 1:
        return

    problem = sameStart.iloc[0]

    contig = chrom.contigs.filter(models.Contig.problem == problem['id']).first()

    if contig is None:
        return

    return contig.getModelSums(db)
