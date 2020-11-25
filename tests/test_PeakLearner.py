from api import JobHandler as jh, PLConfig as cfg
import server.run as slurmrun
import run
import time
import os
import requests


def test_JobHandler():
    testProblem = {'ref': 'chr1', 'start': 521368, 'end': 2634220}
    testTrackInfo = {'ref': 'chr1', 'start': 1506599, 'end': 1510099,
                     'genome': 'hg19', 'hub': 'testHub', 'track': 'testTrack',
                     'name': 'testHub/testTrack'}
    testJob = {'type': 'pregen', 'problem': testProblem, 'trackInfo': testTrackInfo,
               'penalties': [100, 1000, 10000, 100000, 1000000]}

    otherTestProblem = {'ref': 'chr1', 'start': 2684221, 'end': 3845268}
    otherTestTrackInfo = {'ref': 'chr1', 'start': 2971999, 'end': 2986999,
                          'genome': 'hg19', 'hub': 'testHub', 'track': 'testTrack',
                          'name': 'testHub/testTrack'}
    otherTestJob = {'type': 'pregen', 'problem': otherTestProblem, 'trackInfo': otherTestTrackInfo,
                    'penalties': [100, 1000, 10000, 100000, 1000000]}

    # Test Job Adding
    jh.addJob(testJob)

    assert len(jh.getAllJobs({})) == 1

    # Check that duplicate jobs aren't added
    jh.addJob(testJob)

    assert len(jh.getAllJobs({})) == 1

    jh.addJob(otherTestJob)

    assert len(jh.getAllJobs({})) == 2

    # Test getJob

    job = jh.getJob({'id': 0})

    # Fetch with ID doesn't update status
    assert job['status'] == 'New'

    jobData = job['data']

    assert jobData['problem'] == testProblem
    assert jobData['trackInfo'] == testTrackInfo

    job = jh.getJob({})

    assert job['status'] == 'Processing'

    jobData = job['data']

    assert jobData['problem'] == testProblem
    assert jobData['trackInfo'] == testTrackInfo

    # Test Update Job

    jh.updateJob({'id': 0, 'status': 'testStatus'})

    job = jh.getJob({'id': 0})

    assert job['status'] == 'testStatus'

    # Test removing jobs

    jh.removeJob({'id': 0})

    assert len(jh.getAllJobs({})) == 1

    # If job is done, remove it from jobs list
    jh.updateJob({'id': 1, 'status': 'Done'})

    assert len(jh.getAllJobs({})) == 0


serverIp = 'http://127.0.0.1:%s' % cfg.httpServerPort


def test_serverStarted():
    run.startServer()

    time.sleep(1)

    query = {'command': 'getAllJobs', 'args': {}}

    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 204


def test_addHub():
    query = {'command': 'parseHub', 'args': 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'}

    request = requests.post(serverIp, json=query)

    assert request.status_code == 200

    assert request.json() == 'data/TestHub'

    dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

    assert os.path.exists(dataPath)

    hg19path = os.path.join(dataPath, 'genomes', 'hg19')

    assert os.path.exists(hg19path)

    indexed = os.path.join(hg19path, 'hg19.fa.fai')

    assert os.path.exists(indexed)

    problemsTrackList = os.path.join(hg19path, 'problems', 'trackList.json')

    assert os.path.exists(problemsTrackList)


def test_getGenome():
    query = {'command': 'getGenome', 'args': {'name': 'TestHub/aorta_ENCFF115HTK'}}

    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    assert request.json() == 'hg19'


problems = [{'ref': 'chr1', 'start':  10000, 'end': 177417},
            {'ref': 'chr1', 'start':  227417, 'end': 267719},
            {'ref': 'chr1', 'start':  317719, 'end': 471368},
            {'ref': 'chr1', 'start': 521368, 'end': 2634220},
            {'ref': 'chr1', 'start': 2684220, 'end': 3845268},
            {'ref': 'chr1', 'start': 3995268, 'end': 13052998},
            {'ref': 'chr1', 'start': 13102998, 'end': 13219912},
            {'ref': 'chr1', 'start': 13319912, 'end': 13557162},
            {'ref': 'chr1', 'start': 13607162, 'end': 17125658},
            {'ref': 'chr1', 'start': 17175658, 'end': 29878082},
            {'ref': 'chr1', 'start': 30028082, 'end': 103863906},
            {'ref': 'chr1', 'start': 103913906, 'end':  120697156}]




rangeArgs = {'name': 'TestHub/aorta_ENCFF115HTK',
             'ref': 'chr1', 'start': 0, 'end': 120000000}


def test_getProblems():
    query = {'command': 'getProblems', 'args': rangeArgs}
    request = requests.post(serverIp, json=query, timeout=1)

    assert request.status_code == 200

    assert problems == request.json()


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

    jobData = createdJob['data']

    assert jobData['type'] == 'pregen'

    jobProblem = jobData['problem']

    assert jobProblem['ref'] == 'chr1'
    assert jobProblem['start'] == 13607162
    assert jobProblem['end'] == 17125658

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

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    while True:
        query = {'command': 'getModelSummary', 'args': startLabel}
        request = requests.post(serverIp, json=query, timeout=5)
        print('time:', time.time(), '\nstatusCode:', request.status_code, '\n')

        if request.status_code == 200:
            models = request.json()
            print('lenModels\n', len(models))
            contig = models[str(problem['start'])]
            if len(contig) >= len(job['data']['penalties']):
                break

        if (time.time() - startTime) > 240:
            raise Exception

        time.sleep(5)

    expected = [{'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 6306.0, 'penalty': '100', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 0.0, 'fp': 1.0, 'numPeaks': 262.0, 'penalty': '1000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 48.0, 'penalty': '10000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 1.0, 'fn': 1.0, 'fp': 0.0, 'numPeaks': 18.0, 'penalty': '100000', 'possible_fn': 1.0, 'possible_fp': 1.0, 'regions': 1.0},
                {'errors': 0.0, 'fn': 0.0, 'fp': 0.0, 'numPeaks': 0.0, 'penalty': '1000000', 'possible_fn': 0.0, 'possible_fp': 0.0, 'regions': 0.0}]

    assert contig == expected

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

    contig = sums[str(problem['start'])]

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

    numModels = job['data']['numModels']

    started = slurmrun.startAllNewJobs()

    assert started

    startTime = time.time()

    while True:
        query = {'command': 'getModelSummary', 'args': startLabel}
        request = requests.post(serverIp, json=query, timeout=5)

        if request.status_code == 200:
            models = request.json()
            gridContig = models[str(problem['start'])]
            if len(gridContig) >= len(contig) + numModels:
                break

        if (time.time() - startTime) > 240:
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
