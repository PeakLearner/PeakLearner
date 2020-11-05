import threading

jobLock = threading.Lock()
jobs = []

historyLock = threading.Lock()
jobHistory = []

idLock = threading.Lock()
jobIds = 0


# Adds new job to list for slurm server to process
def addJob(data):
    global jobs, jobIds

    idLock.acquire()
    job = {'status': 'New', 'id': jobIds, 'data': data}
    idLock.release()

    jobLock.acquire()
    exists = False
    if len(jobs) < 1:
        idLock.acquire()
        jobIds = jobIds + 1
        idLock.release()
        jobs.append(job)
    else:
        for currentJob in jobs:
            currentData = currentJob['data']
            if not currentData['type'] == data['type']:
                continue
            sameProblem = data['problem'] == currentData['problem']
            sameTrack = data['trackInfo']['name'] == currentData['trackInfo']['name']

            if not sameProblem or not sameTrack:
                continue

            if data['type'] == 'model':
                samePenalty = data['penalty'] == currentData['penalty']

                if samePenalty:
                    exists = True
                    break
            elif data['type'] == 'gridSearch':
                sameMinPenalty = data['minPenalty'] == currentData['minPenalty']
                sameMaxPenalty = data['maxPenalty'] == currentData['maxPenalty']

                if sameMinPenalty and sameMaxPenalty:
                    exists = True
                    break
            else:
                exists = True
                break

        if not exists:
            idLock.acquire()
            jobIds = jobIds + 1
            idLock.release()
            jobs.append(job)

    jobLock.release()

    #TODO: Call slurm server here


# Will get job either by ID or next new job
def getJob(data):
    output = {}

    jobLock.acquire()

    # If ID field
    if 'id' in data:
        for job in jobs:
            if job['id'] == data['id']:
                output = job
                break
            # If no job with ID, stop
        if not output:
            return
    else:
        for job in jobs:
            if job['status'] == 'New':
                output = job
                # If new job is fetched, that job is now being processed so update jobs to reflect that
                updateJob({'id': job['id'], 'status': 'Processing'}, lock=False)
                break

        if not output:
            return

    jobLock.release()

    return output


def updateJob(data, lock=True):
    global jobs

    if 'id' not in data:
        return

    if 'status' not in data:
        return

    newJobList = []
    added = False

    updatedJob = {}

    if data['status'] == 'Done':
        return removeJob(data)

    if lock:
        jobLock.acquire()

    for job in jobs:
        if job['id'] == data['id']:
            job['status'] = data['status']
            updatedJob = job
            added = True
        newJobList.append(job)

    if added:
        jobs = newJobList

    if lock:
        jobLock.release()

    return updatedJob


def removeJob(data):
    global jobs

    if 'id' not in data:
        return

    newJobList = []

    removedJob = {}

    jobLock.acquire()

    for job in jobs:
        # If job to delete, move it to history
        if job['id'] == data['id']:
            historyLock.acquire()
            jobHistory.append(job)
            removedJob = job
            historyLock.release()
        # If not job to delete, re add to job list
        else:
            newJobList.append(job)

    jobs = newJobList

    jobLock.release()

    return removedJob


def getAllJobs(data):
    return jobs
