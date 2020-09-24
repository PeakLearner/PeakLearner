jobs = []
jobHistory = []
jobIds = 0


# Adds new job to list for slurm server to process
def addJob(data):
    global jobs, jobIds

    job = {'status': 'new', 'id': jobIds, 'data': data}
    jobIds = jobIds + 1
    jobs.append(job)

    #TODO: Call slurm server here


# Will get job either by ID or next new job
def getJob(data):
    global jobs, jobIds
    output = {}

    # If ID field
    if data['id']:
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

        if not output:
            return

    return output


def updateJob(data):
    global jobs, jobIds
    if not data['id']:
        return

    if not data['status']:
        return

    newJobList = []

    for job in jobs:
        if job['id'] == data['id']:
            job['status'] = data['status']
        newJobList.append(job)

    jobs = newJobList


def removeJob(data):
    global jobs
    global jobIds

    if not data['id']:
        return

    newJobList = []

    for job in jobs:
        # If job to delete, move it to history
        if job['id'] == data['id']:
            jobHistory.append(job)
        # If not job to delete, re add to job list
        else:
            newJobList.append(job)

    jobs = newJobList
