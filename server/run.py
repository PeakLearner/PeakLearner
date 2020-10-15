import os
import requests
import configparser
import threading
import commands.ModelGeneration as mg
import utils.SlurmConfig as sc


def startOperation():
    if sc.useSlurm:
        return

    # TODO: Multiple jobs per run (If taking the route of cron jobs)
    query = {'command': 'getJob', 'args': {}}

    # TODO: Add error handling
    job = requests.post(sc.remoteServer, json=query)

    # No jobs available
    if job.status_code == 204:
        return

    # Initialize Directory
    if not os.path.exists(sc.dataPath):
        try:
            os.makedirs(sc.defaultDir)
        except OSError:
            return

    if job.status_code == 200:
        jobInfo = job.json()

        data = jobInfo['data']
        jobType = data['type']

        # TODO: Execute this via slurm
        jobTypes(jobType)(data, jobInfo['id'])

        resetQuery = {'command': 'updateJob', 'args': {'id': jobInfo['id'], 'status': 'New'}}
        requests.post(sc.remoteServer, json=resetQuery)


def jobTypes(jobType):
    types = {
        'model': mg.generateModel,
        'pregen': mg.pregenModels,
    }
    return types.get(jobType, None)


if __name__ == '__main__':
    startOperation()
