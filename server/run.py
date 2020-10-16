import os
import requests
import configparser
import threading
import commands.ModelGeneration as mg
import utils.SlurmConfig as sc


def startAllNewJobs():
    if sc.useSlurm:
        return

    query = {'command': 'getAllJobs', 'args': {'id': 'New'}}

    # TODO: Add error handling
    jobs = requests.post(sc.remoteServer, json=query)

    if jobs.status_code == 204:
        return

    # Initialize Directory
    if not os.path.exists(sc.dataPath):
        try:
            os.makedirs(sc.dataPath)
        except OSError:
            return

    if jobs.status_code == 200:
        infoForJobs = jobs.json()

        for job in infoForJobs:
            data = job['data']
            jobType = data['type']

            # TODO: Execute this via slurm
            jobTypes(jobType)(data, job['id'])

            if sc.testing:
                print("Reset")
                resetQuery = {'command': 'updateJob', 'args': {'id': job['id'], 'status': 'New'}}
                requests.post(sc.remoteServer, json=resetQuery)



def jobTypes(jobType):
    types = {
        'model': mg.model,
        'pregen': mg.pregen,
    }
    return types.get(jobType, None)


if __name__ == '__main__':
    startAllNewJobs()
