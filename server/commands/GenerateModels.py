import sys
import os
import bbi
import requests
import threading
import pandas as pd
import utils.SlurmConfig as sc


def generateModels(coverageUrl, problemsPath, outputPath):
    # Initialize Directory
    if not os.path.exists(outputPath):
        try:
            os.makedirs(outputPath)
        except OSError:
            return

    coveragePath = '%scoverage.bigWig' % outputPath

    problemThreads = []

    if not os.path.exists(coveragePath):
        coverageRequest = requests.get(coverageUrl, allow_redirects=True)
        open(coveragePath, 'wb').write(coverageRequest.content)

        if not coverageRequest.status_code == 200:
            return

    with open(problemsPath) as problems:
        problem = problems.readline()

        # TODO: Thread problems without destroying memory
        while not problem == '':
            problemVals = problem.rstrip().split(sep='\t')

            chrom = problemVals[0]
            start = int(problemVals[1])
            end = int(problemVals[2])

            problemFolder = '%s%s-%s-%s/' % (outputPath, chrom, start, end)

            # Initialize Directory
            if not os.path.exists(problemFolder):
                try:
                    os.makedirs(problemFolder)
                except OSError:
                    return

            problemCoveragePath = '%scoverage.bedGraph' % problemFolder

            if not os.path.exists(problemCoveragePath):
                with bbi.open(coveragePath) as coverage:
                    try:
                        coverageInterval = coverage.fetch_intervals(chrom, start, end, iterator=True)
                        gapFixInProblemCoverage(coverageInterval, problemCoveragePath, chrom, start, end)
                    except KeyError:
                        print("Removing Dir", problemFolder)
                        os.rmdir(problemFolder)
                        problem = problems.readline()
                        continue

            # TODO: Use penalty values learned from the system
            penalties = ['1', '10', '100']

            for penalty in penalties:
                modelCommand = 'Rscript commands/GenerateModel.R %s %s' % (problemFolder, penalty)
                if sc.multithread:
                    modelThread = threading.Thread(target=os.system, args=(modelCommand,))
                    modelThread.start()
                    problemThreads.append([problemCoveragePath, modelThread])   
                else:
                    os.system(modelCommand)

            problem = problems.readline()

    # First join all threads
    for problem in problemThreads:
        problem[1].join()

    # All models need to be done processing for cleanup to occur
    if not sc.testing:
        for problem in problemThreads:
            if os.path.exists(problem[0]):
                os.remove(problem[0])

        os.remove(coveragePath)


def gapFixInProblemCoverage(interval, outputPath, chrom, problemStart, problemEnd):
    output = []

    prevEnd = problemStart

    for data in interval:
        # If current data's start doesn't have the previous end
        if prevEnd < data[1]:
            # Add zero valued data from prev end to current start
            output.append((chrom, prevEnd, data[1], 0))

        output.append(data)

        prevEnd = data[2]

    # If end of data doesn't completely go to end of problem
    # I don't think this is strictly necessary
    if prevEnd < problemEnd:
        # Output[0][0] = the chrom
        output.append((chrom, prevEnd, problemEnd, 0))

    output = pd.DataFrame(output)

    output.to_csv(outputPath, sep='\t', float_format='%d', header=False, index=False)


def main():
    coverageUrl = problemsPath = outputPath = ''

    complete = False

    if len(sys.argv) == 1:
        return

    if len(sys.argv) >= 2:
        coverageUrl = sys.argv[1]

    if len(sys.argv) >= 3:
        problemsPath = sys.argv[2]

    if len(sys.argv) >= 4:
        outputPath = sys.argv[3]

        complete = True

    if not complete:
        print("Invalid number of args")
        return

    generateModels(coverageUrl, problemsPath, outputPath)


if __name__ == '__main__':
    main()
