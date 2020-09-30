import sys
import os


def generateModels(coverage, problems, output):

    # Initialize Directory
    if not os.path.exists(output):
        try:
            os.makedirs(output)
        except OSError:
            return

    with open(problems) as problems:
        problem = problems.readline()

        while not problem == '':
            problemVals = problem.rstrip().split(sep='\t')

            ref = problemVals[0]
            start = problemVals[1]
            end = problemVals[2]

            problemFolder = '%s%s-%s-%s/' % (output, ref, start, end)

            # Initialize Directory
            if not os.path.exists(problemFolder):
                try:
                    os.makedirs(problemFolder)
                except OSError:
                    return

            # Need to get coverage file here
            # Will need to use bigWigToBedGraph from UCSC

            problem = problems.readline()


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
