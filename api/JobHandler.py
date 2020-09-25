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
    job = {'status': 'new', 'id': jobIds, 'data': data}
    jobIds = jobIds + 1
    idLock.release()

    jobLock.acquire()
    jobs.append(job)
    jobLock.release()

    #TODO: Call slurm server here


# Will get job either by ID or next new job
def getJob(data):
    output = {}

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
            if job['status'] == 'new':
                output = job
                # If new job is fetched, that job is now being processed so update jobs to reflect that
                updateJob({'id': job['id'], 'status': 'Processing'})
                break

        if not output:
            return

    return output


def updateJob(data):
    global jobs

    if 'id' not in data:
        return

    if 'status' not in data:
        return

    newJobList = []
    added = False

    jobLock.acquire()

    for job in jobs:
        if job['id'] == data['id']:
            job['status'] = data['status']
            added = True
        newJobList.append(job)

    if added:
        jobs = newJobList

    jobLock.release()


def removeJob(data):
    global jobs

    if 'id' not in data:
        return

    newJobList = []

    jobLock.acquire()

    for job in jobs:
        # If job to delete, move it to history
        if job['id'] == data['id']:
            historyLock.acquire()
            jobHistory.append(job)
            historyLock.release()
        # If not job to delete, re add to job list
        else:
            newJobList.append(job)

    jobs = newJobList

    jobLock.release()


def getAllJobs(data):
    return jobs
