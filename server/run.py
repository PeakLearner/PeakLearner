import os
import requests
import commands.ModelGeneration as mg
import utils.SlurmConfig as cfg


def startAllNewJobs():
    query = {'command': 'getAllJobs', 'args': {'id': 'New'}}

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

        for job in infoForJobs:
            if job['status'].lower() == 'new':
                if cfg.useSlurm:
                    createSlurmJob(job)
                else:
                    mg.startJob(job['id'])


def createSlurmJob(job):

    jobName = 'PeakLearner-%d' % job['id']

    jobString = '#!/bin/bash\n'

    jobString += '#SBATCH --job-name=%s\n' % job['id']

    jobString += '#SBATCH --output=%s%s/%s.txt\n' % (cfg.dataPath, cfg.slurmUser, jobName)
    jobString += '#SBATCH --chdir=%s%s\n' % (cfg.dataPath, cfg.slurmUser)

    # TODO: Make resource allocation better
    jobString += '#SBATCH --time=1:00\n'
    jobString += '#SBATCH --mem=1024\n'
    jobString += '#SBATCH --c 1\n'

    jobString += 'module load anaconda3\n'
    jobString += 'module load R\n'

    jobString += 'conda activate %s\n' % cfg.condaVenvPath

    jobString += 'srun python3 commands/ModelGeneration.py %s\n' % (job['id'])

    command = 'sbatch %s' % jobString

    os.system(command)


if __name__ == '__main__':
    startAllNewJobs()
