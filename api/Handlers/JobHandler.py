from api import PLdb as db


# Adds new job to list for slurm server to process
def updateJob(data):
    jobs = db.Job('jobs')

    updated, current = jobs.add(data)

    return updated


# Will get job either by ID or next new job
def getJob(data):
    jobs = db.Job('jobs').get()

    jobOutput = {}

    for job in jobs:
        if job['id'] == data['id']:
            jobOutput = job

    return jobOutput


def removeJob(data):
    jobs = db.Job('jobs')

    return jobs.remove(data)


def getAllJobs(data):
    output = db.Job('jobs').get()
    if len(output) >= 1:
        return output
