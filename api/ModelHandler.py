import os
import api.TrackHandler as th
import api.PLConfig as pl


def getModel(data):
    return []


def newLabel(data):
    return updateLabelProblem(data, 1)


def deleteLabel(data):
    updateLabelProblem(data, -1)
    return updateModel(data)


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

                for problem in problems:
                    if ref == problem['ref'] and start == problem['start'] and end == problem['end']:

                        numLabels = int(lineVals[3]) + update

                        skip = numLabels < 1

                        problemLabels = '%s\t%s\t%s\t%d\n' % (ref, start, end, numLabels)
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


# Calls to this function probably need to be multithreaded to not slow down the process
def updateModel(data):
    data['hub'] = data['name'].split('/')[0]

    genome = th.getGenome(data)

    data['genome'] = genome

    problems = th.getProblems(data)

    print(data)

    # For models, update label error using data

    # Determine new models to generate, if needed


    return data
