import os
import pandas as pd
import api.TrackHandler as th
import api.PLConfig as pl


def getModel(data):
    return []


def newLabel(data):
    return updateLabelProblem(data, 1)


def deleteLabel(data):
    updateLabelProblem(data, -1)
    deleteLabelFromModelErrors(data)
    return updateModels(data)


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
                modelPath = '%s%s' % (modelsPath, file)
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








def updateLabelProblem(data, update):
    data['hub'] = data['name'].split('/')[0]

    genome = th.getGenome(data)

    data['genome'] = genome

    problems = th.getProblems(data)

    if len(problems) < 0:
        return

    output = []

    problemLabelsPath = '%s%s_ProblemLabels.bedGraph' % (pl.dataPath, data['name'])

    if not os.path.exists(problemLabelsPath):
        for problem in problems:
            output.append("%s\t%s\t%s\t1\n" %
                          (problem['ref'], problem['start'], problem['end']))
    else:
        with open(problemLabelsPath) as problemLabelsFile:
            problemLabels = problemLabelsFile.readline()

            while not problemLabels == '':
                lineVals = problemLabels.split(sep='\t')
                ref = lineVals[0]
                start = int(lineVals[1])
                end = int(lineVals[2])

                skip = False

                # When problems is empty, this loop doesn't run
                for problem in problems:
                    if ref == problem['ref'] and start == problem['start'] and end == problem['end']:

                        numLabels = int(lineVals[3]) + update

                        skip = numLabels < 1

                        problemLabels = '%s\t%s\t%s\t%d\n' % (ref, start, end, numLabels)
                        # Remove problem as it has been updated, and no longer needs to be searched for
                        problems.remove(problem)

                    if ref > problem['ref'] and start > problem['start']:
                        output.append('%s\t%s\t%s\t1\n' % (problem['ref'], problem['start'], problem['end']))
                        problems.remove(problem)

                if not skip:
                    output.append(problemLabels)

                problemLabels = problemLabelsFile.readline()

        # If there are any problems left over, add them
        for problem in problems:
            output.append('%s\t%d\t%d\t1\n' % (problem['ref'], problem['start'], problem['end']))

    open(problemLabelsPath, 'w').writelines(output)

    return problemLabelsPath


def updateModels(data):
    data['hub'] = data['name'].split('/')[0]

    data['track'] = data['name'].split('/')[-1]

    genome = th.getGenome(data)

    data['genome'] = genome

    start = data['start']
    end = data['end']

    # This is the problems that the label update is in
    problems = th.getProblems(data)

    for problem in problems:
        # data path, hub path, track path, problem path
        modelsPath = '%s%s/%s/%s-%s-%s/' % (pl.dataPath, data['hub'], data['track'],
                                           problem['ref'], problem['start'], problem['end'])

        if not os.path.exists(modelsPath):
            return

        files = os.listdir(modelsPath)

        modelErrors = []

        for file in files:
            # If the file is a model
            # TODO: Make this smarter, only update relative models and/or prune models
            if 'segments' in file:
                modelPath = '%s%s' % (modelsPath, file)

                modelLabelData = []

                with open(modelPath) as model:
                    modelData = model.readline()

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

                        modelData = model.readline()

                errorFile = putLabelError(modelLabelData, data, modelPath)
                error = calculateLabelFileOverallError(errorFile)

                if error > 1:
                    continue

                modelErrors.append('%d\t%f\n' % (getPenalty(file), error))

        modelSummaryPath = '%s/modelSummary.txt' % modelsPath

        open(modelSummaryPath, 'w').writelines(modelErrors)

    return data


def calculateLabelFileOverallError(modelErrorPath):
    df = pd.read_csv(modelErrorPath, sep='\t', header=None)
    df.columns = ['ref', 'start', 'end', 'label', 'correct', 'incorrect']

    knowns = df[df['label'] != 'unknown']

    # If no knowns in list
    if knowns.size < 1:
        return 2

    errors = knowns.apply(rowErrorCalc, axis=1)

    return errors.mean()


def rowErrorCalc(row):
    return row['correct'] / (row['correct'] + row['incorrect'])


def putLabelError(modelData, data, modelPath):
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

    return saveModelErrorToFile(data, modelPath, correctData, incorrectData)


def saveModelErrorToFile(data, modelPath, correctData, incorrectData):
    modelFile = modelPath.rsplit('/', 1)

    modelErrorFile = '%s/%d_labelError.bedGraph' % (modelFile[0], getPenalty(modelFile[-1]))

    line_to_put = '%s\t%d\t%d\t%s\t%d\t%d\n' % (data['ref'], data['start'], data['end'],
                                                data['label'], correctData, incorrectData)

    if not os.path.exists(modelErrorFile):
        with open(modelErrorFile, 'w') as new:
            print("New LabelErrorFile created at %s", modelErrorFile)
            new.write(line_to_put)
            return data

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

    with open(modelErrorFile, 'w') as f:
        f.writelines(output)

    return modelErrorFile


def getPenalty(filePath):
    # Get penalty value from file
    penaltySplit = filePath.split('=')
    return int(penaltySplit[-1].split('_', 1)[0])
