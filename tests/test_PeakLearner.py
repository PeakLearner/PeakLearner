from api.util import PLConfig as cfg
import server.run as slurmrun
import pandas as pd
import run
import time
import os
import requests

pd.set_option("display.max_rows", None, "display.max_columns", None)
serverIp = 'http://127.0.0.1:%s' % cfg.httpServerPort
cfg.test = True
sleepTime = 600


def test_serverStarted():
    run.startServer()

    time.sleep(1)

    query = {'command': 'getAllJobs', 'args': {}}

    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 204


def test_addHub():
    query = {'command': 'parseHub', 'args': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}

    request = requests.post(serverIp, json=query, timeout=600)

    assert request.status_code == 200

    assert request.json() == 'data/TestHub'

    dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

    assert os.path.exists(dataPath)

    hg19path = os.path.join(dataPath, 'genomes', 'hg19')

    assert os.path.exists(hg19path)

    problemsTrackList = os.path.join(hg19path, 'problems', 'trackList.json')

    assert os.path.exists(problemsTrackList)


def test_getGenome():
    query = {'command': 'getGenome', 'args': {'name': 'TestHub/aorta_ENCFF115HTK'}}

    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    assert request.json() == 'hg19'


problems = [{'chrom': 'chr1', 'chromStart':  10000, 'chromEnd': 177417},
            {'chrom': 'chr1', 'chromStart':  227417, 'chromEnd': 267719},
            {'chrom': 'chr1', 'chromStart':  317719, 'chromEnd': 471368},
            {'chrom': 'chr1', 'chromStart': 521368, 'chromEnd': 2634220},
            {'chrom': 'chr1', 'chromStart': 2684220, 'chromEnd': 3845268},
            {'chrom': 'chr1', 'chromStart': 3995268, 'chromEnd': 13052998},
            {'chrom': 'chr1', 'chromStart': 13102998, 'chromEnd': 13219912},
            {'chrom': 'chr1', 'chromStart': 13319912, 'chromEnd': 13557162},
            {'chrom': 'chr1', 'chromStart': 13607162, 'chromEnd': 17125658},
            {'chrom': 'chr1', 'chromStart': 17175658, 'chromEnd': 29878082},
            {'chrom': 'chr1', 'chromStart': 30028082, 'chromEnd': 103863906},
            {'chrom': 'chr1', 'chromStart': 103913906, 'chromEnd':  120697156}]




rangeArgs = {'name': 'TestHub/aorta_ENCFF115HTK', 'user': 1, 'hub': 'TestHub', 'track': 'aorta_ENCFF115HTK',
             'ref': 'chr1', 'start': 0, 'end': 120000000}


def test_getProblems():
    query = {'command': 'getProblems', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    out = request.json()

    print('getProblemsOutput\n', out, '\n')

    assert problems == out


expectedUrl = 'https://rcdata.nau.edu/genomic-ml/PeakSegFPOP/labels/H3K4me3_TDH_ENCODE/samples/aorta/ENCFF115HTK/coverage.bigWig'


def test_getTrackUrl():
    query = {'command': 'getTrackUrl', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    assert expectedUrl == request.json()


startLabel = rangeArgs.copy()
startLabel['start'] = 15250059
startLabel['end'] = 15251519
endLabel = startLabel.copy()
endLabel['start'] = 15251599
endLabel['end'] = 15252959
noPeakLabel = rangeArgs.copy()
noPeakLabel['start'] = 16089959
noPeakLabel['end'] = 16091959


def test_labels():
    # Blank Label Test
    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 204

    # Add label
    query = {'command': 'addLabel', 'args': startLabel}

    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    serverLabel = request.json()[0]

    assert serverLabel['ref'] == startLabel['ref']
    assert serverLabel['start'] == startLabel['start']
    assert serverLabel['end'] == startLabel['end']
    assert serverLabel['label'] == 'unknown'

    # Update Label

    updateLabel = startLabel.copy()

    updateLabel['label'] = 'peakStart'

    query = {'command': 'updateLabel', 'args': updateLabel}

    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    serverLabel = request.json()[0]

    assert serverLabel['label'] == 'peakStart'

    query = {'command': 'getAllJobs', 'args': {}}

    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    createdJob = request.json()[0]

    assert createdJob['status'] == 'New'

    jobData = createdJob['jobData']

    assert createdJob['jobType'] == 'pregen'

    jobProblem = jobData['problem']

    assert jobProblem['chrom'] == 'chr1'
    assert jobProblem['chromStart'] == 13607162
    assert jobProblem['chromEnd'] == 17125658

    # Try adding another label
    query = {'command': 'addLabel', 'args': endLabel}

    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    labels = request.json()

    assert len(labels) == 2
    assert labels[1]['start'] == endLabel['start']

    # Update second label
    updateAnother = endLabel.copy()
    updateAnother['label'] = 'peakEnd'

    query = {'command': 'updateLabel', 'args': updateAnother}

    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    query = {'command': 'getAllJobs', 'args': {}}

    request = requests.post(serverIp, json=query, timeout=5)

    # Check that system doesn't create duplicate jobs
    assert len(request.json()) == 1

    job = request.json()[0]

    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200

    labels = request.json()

    assert len(labels) == 2

    assert labels[0]['label'] == 'peakStart'
    assert labels[1]['label'] == 'peakEnd'

    # Remove Labels
    for label in labels:
        label['name'] = rangeArgs['name']
        query = {'command': 'removeLabel', 'args': label}
        request = requests.post(serverIp, json=query, timeout=5)

        assert request.status_code == 200

    query = {'command': 'getLabels', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 204

    # Remove job, could cause issues in next test

    query = {'command': 'removeJob', 'args': job}
    request = requests.post(serverIp, json=query, timeout=5)

    assert request.status_code == 200


def test_models():
    # Add initial label
    query = {'command': 'addLabel', 'args': startLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    # Update Label to create job
    updateLabel = startLabel.copy()
    updateLabel['label'] = 'peakStart'
    query = {'command': 'updateLabel', 'args': updateLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    query = {'command': 'getAllJobs', 'args': {}}
    request = requests.post(serverIp, json=query, timeout=5)
    jobs = request.json()
    assert len(jobs) == 1

    query = {'command': 'getProblems', 'args': startLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    problems = request.json()

    assert len(problems) == 1

    problem = problems[0]

    job = jobs[0]

    numModels = job['numModels']

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    while True:
        query = {'command': 'getModelSummary', 'args': startLabel}
        request = requests.post(serverIp, json=query, timeout=5)
        print('time:', time.time(), '\nstatusCode:', request.status_code, '\n')

        if request.status_code == 200:
            models = request.json()
            problemSum = models[str(problem['chromStart'])]
            if len(problemSum) >= numModels:
                break

        if (time.time() - startTime) > sleepTime:
            raise Exception

        time.sleep(5)

    expected = [{'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 6306.0, 'penalty': '100', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 262.0, 'penalty': '1000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 48.0, 'penalty': '10000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 1.0, 'fp': 0.0, 'numPeaks': 18.0, 'penalty': '100000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 0.0, 'penalty': '1000000', 'possible_fn': 0.0, 'possible_fp': 0.0, 'regions': 0.0}]

    assert problemSum == expected

    # Add label with no update
    query = {'command': 'addLabel', 'args': endLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    updateLabel = endLabel.copy()
    updateLabel['label'] = 'peakEnd'
    query = {'command': 'updateLabel', 'args': updateLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    query = {'command': 'getAllJobs', 'args': {}}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 204

    query = {'command': 'getModelSummary', 'args': startLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    sums = request.json()

    contig = sums[str(problem['chromStart'])]

    expected = [{'regions': 2, 'fp': 2, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 2, 'penalty': '100', 'numPeaks': 6306},
                {'regions': 2, 'fp': 2, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 2, 'penalty': '1000', 'numPeaks': 262},
                {'regions': 2, 'fp': 0, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 0, 'penalty': '10000', 'numPeaks': 48},
                {'regions': 2, 'fp': 0, 'possible_fp': 2, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '100000', 'numPeaks': 18},
                {'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0, 'errors': 0, 'penalty': '1000000', 'numPeaks': 0}]

    assert contig == expected

    # Add Label with grid search
    query = {'command': 'addLabel', 'args': noPeakLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    updateLabel = noPeakLabel.copy()
    updateLabel['label'] = 'noPeak'
    query = {'command': 'updateLabel', 'args': updateLabel}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    query = {'command': 'getAllJobs', 'args': {}}
    request = requests.post(serverIp, json=query, timeout=5)
    assert request.status_code == 200

    jobs = request.json()

    assert len(jobs) == 1

    job = jobs[0]

    numModels += job['numModels']

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    while True:
        query = {'command': 'getModelSummary', 'args': startLabel}
        request = requests.post(serverIp, json=query, timeout=5)

        if request.status_code == 200:
            models = request.json()
            gridContig = models[str(problem['chromStart'])]
            if len(gridContig) >= numModels:
                break

        if (time.time() - startTime) > sleepTime:
            raise Exception

        time.sleep(5)

    expected = [{'regions': 3, 'fp': 3, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 3, 'penalty': '100', 'numPeaks': 6306},
                {'regions': 3, 'fp': 3, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 3, 'penalty': '1000', 'numPeaks': 262},
                {'regions': 3, 'fp': 1, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 1, 'penalty': '10000', 'numPeaks': 48},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0, 'penalty': '18181.818181818184', 'numPeaks': 38},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0, 'penalty': '26363.636363636364', 'numPeaks': 33},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0, 'penalty': '34545.454545454544', 'numPeaks': 32},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0, 'penalty': '42727.27272727273', 'numPeaks': 27},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '50909.09090909091', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '59090.90909090909', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '67272.72727272726', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '75454.54545454546', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '83636.36363636363', 'numPeaks': 20},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '91818.18181818182', 'numPeaks': 20},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2, 'penalty': '100000', 'numPeaks': 18},
                {'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0, 'errors': 0, 'penalty': '1000000', 'numPeaks': 0}]

    assert gridContig == expected


def test_shutdownServer():
     run.shutdown()
