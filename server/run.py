import os
import requests
import time
import tempfile
import ModelGeneration as mg
import SlurmConfig as cfg


def startAllNewJobs():
    query = {'command': 'getAllJobs', 'args': {'status': 'New'}}

    # TODO: Add error handling
    jobs = requests.post(cfg.remoteServer, json=query)

    if jobs.status_code == 204:
        return False

    # Initialize Directory
    if not os.path.exists(cfg.dataPath):
        try:
            os.makedirs(cfg.dataPath)
        except OSError:
            return False

    if jobs.status_code == 200:
        infoForJobs = jobs.json()

        print(len(infoForJobs))

        for job in infoForJobs:
            if job['status'].lower() == 'new':

                startQuery = {'command': 'updateJob', 'args':{'id': job['id'], 'status': 'Queued'}}
                startRequest = requests.post(cfg.remoteServer, json=startQuery)

                if not startRequest.status_code == 200:
                    continue

                print("Starting job with ID", job['id'], "and type", job['data']['type'])
                if cfg.useSlurm:
                    createSlurmJob(job)
                else:
                    mg.startJob(job['id'])

        return True

    return False


def createSlurmJob(job):
    # TODO: Calculate required CPUs for job
    numCpus = 5
    if numCpus > cfg.maxCPUsPerJob:
        numCpus = cfg.maxCPUsPerJob

    jobName = 'PeakLearner-%d' % job['id']

    jobString = '#!/bin/bash\n'

    jobString += '#SBATCH --job-name=%s\n' % jobName

    jobString += '#SBATCH --output=%s\n' % os.path.join(os.getcwd(), 'data/', jobName + '.txt')
    jobString += '#SBATCH --chdir=%s\n' % os.getcwd()

    # TODO: Make resource allocation better
    jobString += '#SBATCH --time=2:00\n'
    jobString += '#SBATCH --cpus-per-task=%d\n' % numCpus

    if cfg.monsoon:
        jobString += '#SBATCH --mem=1024\n'
        jobString += 'module load anaconda3\n'
        jobString += 'module load R\n'
        jobString += 'conda activate %s\n' % cfg.condaVenvPath

    jobString += 'srun python3 %s %s\n' % ('ModelGeneration.py', job['id'])

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh') as temp:
        temp.write(jobString)
        temp.flush()
        temp.seek(0)

        command = 'sbatch %s' % temp.name

        os.system(command)


if __name__ == '__main__':
    startTime = time.time()

    if cfg.useCron:
        timeDiff = lambda: time.time() - startTime

        while timeDiff() < cfg.timeToRun:
            startAllNewJobs()
            time.sleep(1)
    else:
        startAllNewJobs()

        endTime = time.time()

        print("Start Time:", startTime, "End Time", endTime)
