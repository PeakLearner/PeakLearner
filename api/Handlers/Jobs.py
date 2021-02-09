from api.util import PLdb as db
from api.Handlers.Handler import Handler


class JobHandler(Handler):
    """Handles Job Commands"""

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        # TODO: Add update/delete/info
        return {'get': getJob,
                'add': addJob,
                'update': updateJob,
                'remove': removeJob,
                'getAll': getAllJobs}


def addJob(job):
    # Get list of current job keys
    keys = db.Job.db_key_tuples()

    # If no jobs, just add it
    if len(keys) < 1:
        addJobToDb(job)
        return job

    exists = False
    # Check for similar jobs
    for key in keys:
        jobToCheck = db.Job(*key).get()

        # Is there a better way to do this?
        if not jobToCheck['user'] == job['user']:
            continue

        if not jobToCheck['hub'] == job['hub']:
            continue

        if not jobToCheck['track'] == job['track']:
            continue

        if not jobToCheck['problem'] == job['problem']:
            continue

        if not jobToCheck['jobType'] == job['jobType']:
            continue

        if jobToCheck['status'] == 'Done':
            continue

        # TODO: compare given a jobType

        exists = True

    if not exists:
        addJobToDb(job)
        return job


def addJobToDb(job):
    txn = db.getTxn()
    jobId = db.JobInfo('Id').incrementId(txn=txn)
    job['id'] = jobId
    job['status'] = 'New'

    db.Job(jobId).put(job, txn=txn)

    txn.commit()
    return job


# Adds new job to list for slurm server to process
def updateJob(job):
    txn = db.getTxn()
    jobDb = db.Job(job['id'])
    toUpdate = jobDb.get(txn=txn, write=True)

    if len(toUpdate.keys()) < 1:
        txn.commit()
        raise Exception(job)

    for key in job.keys():
        toUpdate[key] = job[key]

    jobDb.put(toUpdate, txn=txn)
    returnVal = toUpdate
    txn.commit()

    return returnVal


# Will get job either by ID or next new job
def getJob(data):
    return db.Job(data['id']).get()


def removeJob(data):
    txn = db.getTxn()
    output = db.Job(data['id']).put(None, txn=txn)
    txn.commit()
    return output


def getAllJobs(data):
    jobs = []

    for key in db.Job.db_key_tuples():
        jobs.append(db.Job(*key).get())

    return jobs
