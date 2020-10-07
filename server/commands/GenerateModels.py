import sys
import os
import bbi
import requests
import pandas as pd


def generateModels(coverageUrl, problemsPath, outputPath):

    # Initialize Directory
    if not os.path.exists(outputPath):
        try:
            os.makedirs(outputPath)
        except OSError:
            return

    coveragePath = '%scoverage.bigWig' % outputPath

    if not os.path.exists(coveragePath):
        coverageRequest = requests.get(coverageUrl, allow_redirects=True)
        open(coveragePath, 'wb').write(coverageRequest.content)

        if not coverageRequest.status_code == 200:
            return

    with bbi.open(coveragePath) as coverageFile:
        with open(problemsPath) as problems:
            problem = problems.readline()

            # TODO: Thread this
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
                    try:
                        coverageInterval = coverageFile.fetch_intervals(chrom, start, end, iterator=True)
                        coverageOutput = []
                        prevEnd = start

                        # This loop fills in gaps inside the problems with 0 value data
                        # I assume this is happening due to some type of compression where 0 value data is removed
                        for line in coverageInterval:

                            if prevEnd < line[1]:
                                coverageOutput.append((line[0], prevEnd, line[1], 0))

                            coverageOutput.append(line)

                            prevEnd = line[2]

                        # If end doesn't go all the way to end of problem
                        if prevEnd < end:
                            coverageOutput.append((line[0], prevEnd, end, 0))

                        problemCoverageOutput = pd.DataFrame(coverageOutput)

                        problemCoverageOutput.to_csv(problemCoveragePath, sep='\t', float_format='%d', header=False, index=False)

                    except KeyError:
                        print("Removing Dir", problemFolder)
                        os.rmdir(problemFolder)
                        return

                # TODO: Generate Model(s)
                penalties = ['1']

                for penalty in penalties:
                    modelCommand = 'Rscript commands/GenerateModel.R %s %s' % (problemFolder, penalty)
                    os.system(modelCommand)

                problem = problems.readline()

    # Remove coverage file at end
    # os.remove(coveragePath)


def generateModel(coveragePath, penalty):
    print("Coverage Path", coveragePath)
    print("Penalty", penalty)


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
