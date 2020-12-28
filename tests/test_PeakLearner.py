from api.util import PLConfig as cfg
import server.run as slurmrun
import pandas as pd
import run
import time
import os
import requests

pd.set_option("display.max_rows", None, "display.max_columns", None)
serverURL = 'http://127.0.0.1:%s/' % cfg.httpServerPort
cfg.testing()
sleepTime = 600


def test_serverStarted():
    run.startServer()

    time.sleep(1)

    request = requests.get(serverURL)

    assert request.status_code == 200


def test_addHub():
    query = {'command': 'parseHub', 'args': {'hubUrl': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}}

    uploadHubUrl = '%suploadHubUrl/' % serverURL

    request = requests.post(uploadHubUrl, json=query, timeout=sleepTime)

    assert request.status_code == 200

    assert request.json() == '/1/TestHub/'

    dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

    assert os.path.exists(dataPath)

    hg19path = os.path.join(dataPath, 'genomes', 'hg19')

    assert os.path.exists(hg19path)

    problemsTrackList = os.path.join(hg19path, 'problems', 'trackList.json')

    assert os.path.exists(problemsTrackList)


user = 1
hub = 'TestHub'
track = 'aorta_ENCFF115HTK'
hubURL = '%s%s/%s/' % (serverURL, user, hub)
trackURL = '%s%s/' % (hubURL, track)

expectedTrackKeys = ['aorta_ENCFF115HTK', 'aorta_ENCFF502AXL']


def test_getHubInfo():
    hubInfoURL = '%sinfo/' % hubURL
    request = requests.get(hubInfoURL)

    assert request.status_code == 200

    requestOutput = request.json()

    assert requestOutput['genome'] == 'hg19'

    assert len(requestOutput['tracks']) == 2
    for trackKey in requestOutput['tracks']:
        assert trackKey in expectedTrackKeys


expectedUrl = 'https://rcdata.nau.edu/genomic-ml/PeakSegFPOP/labels/H3K4me3_TDH_ENCODE/samples/aorta/ENCFF115HTK/coverage.bigWig'
trackInfoURL = '%sinfo/' % trackURL


def test_getTrackInfo():
    request = requests.get(trackInfoURL)

    assert request.status_code == 200

    requestOutput = request.json()

    assert requestOutput['key'] == track

    assert requestOutput['url'] == expectedUrl


labelURL = '%slabels/' % trackURL
jobsURL = '%sjobs/' % serverURL
rangeArgs = {'ref': 'chr1', 'start': 0, 'end': 120000000}
startLabel = rangeArgs.copy()
startLabel['start'] = 15250059
startLabel['end'] = 15251519
endLabel = startLabel.copy()
endLabel['start'] = 15251599
endLabel['end'] = 15252959
noPeakLabel = startLabel.copy()
noPeakLabel['start'] = 16089959
noPeakLabel['end'] = 16091959


def test_labels():
    # Blank Label Test
    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert len(request.json()) == 0

    # Add label
    query = {'command': 'add', 'args': startLabel}
    request = requests.post(labelURL, json=query)

    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    assert len(request.json()) == 1

    serverLabel = request.json()[0]

    assert serverLabel['ref'] == startLabel['ref']
    assert serverLabel['start'] == startLabel['start']
    assert serverLabel['end'] == startLabel['end']
    assert serverLabel['label'] == 'unknown'

    # Update Label

    updateLabel = startLabel.copy()

    updateLabel['label'] = 'peakStart'

    query = {'command': 'update', 'args': updateLabel}

    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    serverLabel = request.json()[0]

    assert serverLabel['label'] == 'peakStart'

    query = {'command': 'getAll', 'args': {}}

    request = requests.post(jobsURL, json=query)

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
    query = {'command': 'add', 'args': endLabel}

    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    labels = request.json()

    assert len(labels) == 2
    assert labels[1]['start'] == endLabel['start']

    # Update second label
    updateAnother = endLabel.copy()
    updateAnother['label'] = 'peakEnd'
    query = {'command': 'update', 'args': updateAnother}

    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    query = {'command': 'getAll', 'args': {}}

    request = requests.post(jobsURL, json=query)

    # Check that system doesn't create duplicate jobs
    assert len(request.json()) == 1

    job = request.json()[0]

    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert request.status_code == 200

    labels = request.json()

    assert len(labels) == 2

    assert labels[0]['label'] == 'peakStart'
    assert labels[1]['label'] == 'peakEnd'

    # Remove Labels
    for label in labels:
        query = {'command': 'remove', 'args': label}
        request = requests.post(labelURL, json=query)

        assert request.status_code == 200

    query = {'command': 'get', 'args': rangeArgs}
    request = requests.post(labelURL, json=query)

    assert len(request.json()) == 0

    # Remove job, could cause issues in next test

    query = {'command': 'remove', 'args': job}
    request = requests.post(jobsURL, json=query)

    assert request.status_code == 200


modelsUrl = '%smodels/' % trackURL


def test_models():
    # Add initial label
    query = {'command': 'add', 'args': startLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    # Update Label to create job
    updateLabel = startLabel.copy()
    updateLabel['label'] = 'peakStart'
    query = {'command': 'update', 'args': updateLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    query = {'command': 'getAll', 'args': {}}
    request = requests.post(jobsURL, json=query)
    jobs = request.json()
    assert len(jobs) == 1

    query = {'command': 'getProblems', 'args': startLabel}
    request = requests.post(trackInfoURL, json=query)
    assert request.status_code == 200

    problems = request.json()

    assert len(problems) == 1

    problem = problems[0]

    job = jobs[0]

    numModels = job['numModels']

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    problemSum = checkModelSumLoop(startLabel, startTime, problem, numModels)

    expected = [{'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 6306.0, 'penalty': '100', 'possible_fn': 1.0,
                 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 262.0, 'penalty': '1000', 'possible_fn': 1.0,
                 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 48.0, 'penalty': '10000', 'possible_fn': 1.0,
                 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 1.0, 'fp': 0.0, 'numPeaks': 18.0, 'penalty': '100000', 'possible_fn': 1.0,
                 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 0.0, 'penalty': '1000000', 'possible_fn': 0.0,
                 'possible_fp': 0.0, 'regions': 0.0}]

    assert problemSum == expected

    # Add label with no update
    query = {'command': 'add', 'args': endLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    updateLabel = endLabel.copy()
    updateLabel['label'] = 'peakEnd'
    query = {'command': 'update', 'args': updateLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    query = {'command': 'getAll', 'args': {}}
    request = requests.post(jobsURL, json=query)

    assert request.json() is None

    query = {'command': 'getModelSummary', 'args': startLabel}
    request = requests.post(modelsUrl, json=query)
    assert request.status_code == 200

    sums = request.json()

    contig = sums[str(problem['chromStart'])]

    expected = [{'regions': 2, 'fp': 2, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 2, 'penalty': '100',
                 'numPeaks': 6306},
                {'regions': 2, 'fp': 2, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 2, 'penalty': '1000',
                 'numPeaks': 262},
                {'regions': 2, 'fp': 0, 'possible_fp': 2, 'fn': 0, 'possible_fn': 2, 'errors': 0,
                 'penalty': '10000', 'numPeaks': 48},
                {'regions': 2, 'fp': 0, 'possible_fp': 2, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '100000', 'numPeaks': 18},
                {'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0, 'errors': 0,
                 'penalty': '1000000', 'numPeaks': 0}]

    assert contig == expected

    # Add Label with grid search
    query = {'command': 'add', 'args': noPeakLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    updateLabel = noPeakLabel.copy()
    updateLabel['label'] = 'noPeak'
    query = {'command': 'update', 'args': updateLabel}
    request = requests.post(labelURL, json=query)
    assert request.status_code == 200

    query = {'command': 'getAll', 'args': {}}
    request = requests.post(jobsURL, json=query)
    assert request.status_code == 200

    jobs = request.json()

    assert len(jobs) == 1

    job = jobs[0]

    numModels += job['numModels']

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    gridContig = checkModelSumLoop(startLabel, startTime, problem, numModels)

    expected = [{'regions': 3, 'fp': 3, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 3, 'penalty': '100',
                 'numPeaks': 6306},
                {'regions': 3, 'fp': 3, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 3, 'penalty': '1000',
                 'numPeaks': 262},
                {'regions': 3, 'fp': 1, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 1,
                 'penalty': '10000', 'numPeaks': 48},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0,
                 'penalty': '18181.818181818184', 'numPeaks': 38},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0,
                 'penalty': '26363.636363636364', 'numPeaks': 33},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0,
                 'penalty': '34545.454545454544', 'numPeaks': 32},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 0, 'possible_fn': 2, 'errors': 0,
                 'penalty': '42727.27272727273', 'numPeaks': 27},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '50909.09090909091', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '59090.90909090909', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '67272.72727272726', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '75454.54545454546', 'numPeaks': 22},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '83636.36363636363', 'numPeaks': 20},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '91818.18181818182', 'numPeaks': 20},
                {'regions': 3, 'fp': 0, 'possible_fp': 3, 'fn': 2, 'possible_fn': 2, 'errors': 2,
                 'penalty': '100000', 'numPeaks': 18},
                {'regions': 0, 'fp': 0, 'possible_fp': 0, 'fn': 0, 'possible_fn': 0, 'errors': 0,
                 'penalty': '1000000', 'numPeaks': 0}]

    assert gridContig == expected


def checkModelSumLoop(label, startTime, problem, numModels):
    while True:
        query = {'command': 'getModelSummary', 'args': label}
        request = requests.post(modelsUrl, json=query)

        if not len(request.json()) == 0:
            models = request.json()
            gridContig = models[str(problem['chromStart'])]
            print('lenGridContig', len(gridContig))
            if len(gridContig) >= numModels:
                return gridContig

        if (time.time() - startTime) > sleepTime:
            raise Exception

        time.sleep(5)


def test_shutdownServer():
    run.shutdown()
