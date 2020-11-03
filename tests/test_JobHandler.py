from api import JobHandler as jh


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


def test_AddJob():
    jh.addJob(testJob)

    assert len(jh.getAllJobs({})) == 1

    # Check that duplicate jobs aren't added
    jh.addJob(testJob)

    assert len(jh.getAllJobs({})) == 1

    jh.addJob(otherTestJob)

    assert len(jh.getAllJobs({})) == 2


def test_getJob():
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


def test_UpdateJob():
    jh.updateJob({'id': 0, 'status': 'testStatus'})

    job = jh.getJob({'id': 0})

    assert job['status'] == 'testStatus'


def test_removeJob():
    jh.removeJob({'id': 0})

    assert len(jh.getAllJobs({})) == 1

    # If job is done, remove it from jobs list
    jh.updateJob({'id': 1, 'status': 'Done'})

    assert len(jh.getAllJobs({})) == 0
