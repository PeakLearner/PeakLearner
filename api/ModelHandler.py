import os
import threading
import pandas as pd
import api.TrackHandler as th
import api.PLConfig as pl
import api.JobHandler as jh


def getModel(data):
    return []


def deleteLabel(data):
    return deleteLabelFromModelErrors(data)


def deleteLabelFromModelErrors(data):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    genome = th.getGenome(data)

    data['genome'] = genome

    # This is the problems that the label update is in
    problems = th.getProblems(data)

    for problem in problems:
        # data path, hub path, track path, problem path
        modelsPath = '%s%s/%s/%s-%s-%s/' % (pl.dataPath, data['hub'], data['track'],
                                            problem['ref'], problem['start'], problem['end'])

        if not os.path.exists(modelsPath):
            return

        files = os.listdir(modelsPath)

        summaryOutput = []

        for file in files:

            if 'segments' in file:
                penalty = getPenalty(file)
                errorFile = '%s%d_labelError.bedGraph' % (modelsPath, penalty)

                if not os.path.exists(errorFile):
                    return

                segmentOutput = []

                with open(errorFile) as errors:
                    error = errors.readline()

                    while not error == '':
                        errorVals = error.split()

                        if not data['start'] == int(errorVals[1]):
                            segmentOutput.append(error)
                            error = errors.readline()
                            continue

                        if not data['end'] == int(errorVals[2]):
                            segmentOutput.append(error)
                            error = errors.readline()
                            continue

                        # Don't need to append to modelErrors because anything here is getting deleted

                        error = errors.readline()

                open(errorFile, 'w').writelines(segmentOutput)

                penalty = getPenalty(file)

                if len(segmentOutput) > 1:
                    error, numLabels, dataLoss = calculateLabelFileOverallError(errorFile)

                    summaryOutput.append('%d\t%f\t%d\t%f\n' % (penalty, error, numLabels, dataLoss))
                else:
                    summaryOutput.append('%d\t0\t0\t0\n' % penalty)

        modelSummaryPath = '%s/modelSummary.txt' % modelsPath

        open(modelSummaryPath, 'w').writelines(summaryOutput)


def updateModels(data):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    genome = th.getGenome(data)

    data['genome'] = genome

    # This is the problems that the label update is in
    problems = th.getProblems(data)

    for problem in problems:
        # data path, hub path, track path, problem path
        modelsPath = '%s%s/%s/%s-%s-%s/' % (pl.dataPath, data['hub'], data['track'],
                                           problem['ref'], problem['start'], problem['end'])

        if not os.path.exists(modelsPath):
            return

        files = os.listdir(modelsPath)

        summaryOutput = []

        for file in files:
            # If the file is a model
            # TODO: Make this smarter, only update relative models and/or prune models
            if '_Model' in file:
                modelPath = '%s%s' % (modelsPath, file)

                modelLabelData = getLabelModelData(modelPath, data)

                # Error for current model data
                correctData, incorrectData = calculateLabelDataError(modelLabelData, data)
                errorFile = updateModelErrorFile(data, modelPath, correctData, incorrectData)

                error, numLabels, dataLoss = calculateLabelFileOverallError(errorFile)

                summaryOutput.append('%d\t%f\t%d\t%f\n' % (getPenalty(file), error, numLabels, dataLoss))

        if len(summaryOutput) < 1:
            submitPregenJob(problem, data)

        modelSummaryPath = '%s/modelSummary.txt' % modelsPath

        open(modelSummaryPath, 'w').writelines(summaryOutput)

        modelCheckArgs = (problem, data, modelsPath)

        modelCheckThread = threading.Thread(target=checkGenerateNewModels, args=modelCheckArgs)
        modelCheckThread.start()


    return data


def getLabelModelData(modelPath, data):
    start = data['start']
    end = data['end']
    modelLabelData = []

    with open(modelPath) as model:
        modelData = model.readline()

        found = False
        while not modelData == '':
            dataVals = modelData.split()

            dataStart = int(dataVals[1])
            dataEnd = int(dataVals[2])

            lineIfStartIn = (dataStart >= start) and (dataStart <= end)
            lineIfEndIn = (dataEnd >= start) and (dataEnd <= end)
            wrap = (dataStart < start) and (dataEnd > end)

            # If a data value from the model overlaps or is contained in a label
            if lineIfStartIn or lineIfEndIn or wrap:
                modelLabelData.append(dataVals)
                found = True

            # If data is currently being found, it won't get here
            # This should only run if data has been found and data is no longer being found
            elif found:
                break

            modelData = model.readline()

    return modelLabelData


def calculateLabelFileOverallError(modelErrorPath):
    try:
        df = pd.read_csv(modelErrorPath, sep='\t', header=None)
    except pd.errors.EmptyDataError:
        return 2

    df.columns = ['ref', 'start', 'end', 'label', 'correct', 'incorrect']
    dataLoss = df.apply(calculateModelSizeError, axis=1)
    df['dataSizeError'] = dataLoss
    errors = df.apply(calculateRowError, axis=1)
    df['labelError'] = errors

    knowns = df[df['label'] != 'unknown']

    # If no knowns in list
    if knowns.size < 1:
        return 2

    return knowns['labelError'].mean(), knowns['labelError'].size, knowns['dataSizeError'].mean()


def calculateModelSizeError(row):
    return 1-(1/(row['correct'] + row['incorrect']))


def calculateRowError(row):
    label = row['label']

    if label == 'unknown':
        return 0
    if label == 'noPeak':
        if row['incorrect'] >= 1:
            return 1
        return 0
    else:
        if row['correct'] >= 1:
            return 0
        return 1


def calculateLabelDataError(modelData, data):
    label = data['label']
    start = data['start']
    end = data['end']

    # Maybe rework correct/incorrect data to reflect total area for which that model lines width
    correctData = incorrectData = 0

    if label == 'unknown':
        correctData = len(modelData)

    # There has to be a better way to do this, multiple for loops because checking label time is constant time
    # or 2N inside loop
    elif label == 'peak':
        for line in modelData:
            if line[3] == 'peak':
                correctData = correctData + 1
            else:
                incorrectData = incorrectData + 1
    elif label == 'peakStart':
        for line in modelData:
            if line[3] == 'peak':
                peakStart = int(line[1])
                peakEnd = int(line[2])

                # If the start is in the label but not the end
                if peakStart > start and peakEnd > end:
                    correctData = correctData + 1
                else:
                    incorrectData = incorrectData + 1
            else:
                incorrectData = incorrectData + 1
    elif label == 'peakEnd':
        for line in modelData:
            if line[3] == 'peak':
                peakStart = int(line[1])
                peakEnd = int(line[2])

                # If the end is in the label but not the start
                if peakStart < start and peakEnd < end:
                    correctData = correctData + 1
                else:
                    incorrectData = incorrectData + 1
            else:
                incorrectData = incorrectData + 1
    # Any bad labels are classified as noPeak
    else:
        for line in modelData:
            if line[3] == 'peak':
                incorrectData = incorrectData + 1
            else:
                correctData = correctData + 1

    return correctData, incorrectData


def updateModelErrorFile(data, modelPath, correctData, incorrectData):
    modelFile = modelPath.rsplit('/', 1)

    modelErrorFile = '%s/%d_labelError.bedGraph' % (modelFile[0], getPenalty(modelFile[-1]))

    line_to_put = '%s\t%d\t%d\t%s\t%d\t%d\n' % (data['ref'], data['start'], data['end'],
                                                data['label'], correctData, incorrectData)

    if not os.path.exists(modelErrorFile):
        with open(modelErrorFile, 'w') as new:
            print("New LabelErrorFile created at", modelErrorFile)
            new.write(line_to_put)
            return modelErrorFile

    output = []

    with open(modelErrorFile, 'r') as f:

        current_line = f.readline()

        added = False

        while not current_line == '':
            skip = False

            if added:
                output.append(current_line)
                current_line = f.readline()
                continue

            lineVals = current_line.split()

            start = int(lineVals[1])

            # If the same label, update it (skip previous labels line)
            if start == data['start']:
                output.append(line_to_put)
                added = skip = True

            # If new label, add it
            elif start > data['start']:
                output.append(line_to_put)
                added = True

            if not skip:
                output.append(current_line)

            current_line = f.readline()

        if not added:
            output.append(line_to_put)

    with open(modelErrorFile, 'w') as f:
        f.writelines(output)

    return modelErrorFile


def getPenalty(filePath):
    # Get penalty value from file
    penaltySplit = filePath.split('=')
    return int(penaltySplit[-1].split('_', 1)[0])


def checkGenerateNewModels(problem, data, modelsPath):

    modelSummaryPath = '%s/modelSummary.txt' % modelsPath

    try:
        df = pd.read_csv(modelSummaryPath, sep='\t', header=None)
    except pd.errors.EmptyDataError:
        return

    df.columns = ['penalty', 'meanLabelError', 'numLabels', 'meanDataSizeError']

    minDataSize = df[df.meanDataSizeError == df.meanDataSizeError.min()]

    minDataSizeError = minDataSize['meanDataSizeError'].iloc[0]
    minDataSizePenalty = minDataSize['penalty'].iloc[0].item()

    if minDataSizeError > 0.9:
        submitOOMJob(problem, data, minDataSizePenalty)


def submitOOMJob(problem, data, penalty):
    job = {'type': 'model', 'problem': problem, 'data': data, 'penalty': penalty * 10}
    jh.addJob(job)


def submitPregenJob(problem, data):
    job = {'type': 'pregen', 'problem': problem, 'data': data}
    jh.addJob(job)


def putModel(data):
    modelData = data['modelData']
    modelInfo = data['modelInfo']
    problem = modelInfo['problem']
    trackInfo = modelInfo['data']
    penalty = modelInfo['penalty']

    trackPath = '%s%s/%s/' % (pl.dataPath, trackInfo['hub'], trackInfo['track'])
    problemPath = '%s%s-%d-%d/' % (trackPath, problem['ref'], problem['start'], problem['end'])

    if not os.path.exists(problemPath):
        try:
            os.makedirs(problemPath)
        except OSError:
            return

    modelFilePath = '%s%d_Model.bedGraph' % (problemPath, penalty)

    if os.path.exists(modelFilePath):
        return

    with open(modelFilePath, 'w') as model:
        model.writelines(modelData)

    calculateNewModelLabelErrors(modelFilePath, problemPath, penalty, problem, trackInfo)

    return modelInfo


def calculateNewModelLabelErrors(modelFilePath, problemPath, penalty, problem, trackInfo):
    labelQuery = problem
    labelQuery['name'] = '%s/%s' % (trackInfo['hub'], trackInfo['track'])
    labels = th.getLabels(labelQuery)

    errorFile = ''

    for label in labels:
        modelData = getLabelModelData(modelFilePath, label)
        correctData, incorrectData = calculateLabelDataError(modelData, label)
        errorFile = updateModelErrorFile(label, modelFilePath, correctData, incorrectData)

    error, numLabels, dataLoss = calculateLabelFileOverallError(errorFile)

    modelSummary = '%d\t%f\t%d\t%f\n' % (penalty, error, numLabels, dataLoss)

    modelSummaryPath = '%s/modelSummary.txt' % problemPath

    with open(modelSummaryPath, 'a') as summary:
        summary.write(modelSummary)

    modelCheckArgs = (problem, labelQuery, problemPath)

    # Check if more models should be made
    modelCheckThread = threading.Thread(target=checkGenerateNewModels, args=modelCheckArgs)
    modelCheckThread.start()
