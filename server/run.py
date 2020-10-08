import os
import requests
import configparser
import threading
import commands.GenerateModels as gm
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
    if not os.path.exists(sc.defaultDir):
        try:
            os.makedirs(sc.defaultDir)
        except OSError:
            return

    if job.status_code == 200:
        jobInfo = job.json()
        jobData = jobInfo['data']

        # Reset just loaded val, testing purposes only
        reset = {'command': 'updateJob', 'args': {'id': jobInfo['id'], 'status': 'New'}}
        requests.post(sc.remoteServer, json=reset)

        if 'hub' in jobData:
            newHub(jobData)
        else:
            newModel(jobData)


def newModel(data):
    print(data)


def newHub(data):

    newDataFolder = '%s%s/' % (sc.defaultDir, data['hub'])

    if not os.path.exists(newDataFolder):
        try:
            os.makedirs(newDataFolder)
        except OSError:
            return

    hubInfoArgs = {'command': 'getHubInfo', 'args': {'hub': data['hub']}}

    hubRequest = requests.post(sc.remoteServer, json=hubInfoArgs)

    if not hubRequest.status_code == 200:
        return

    hub = hubRequest.json()

    problemsPath = getProblems(hub)

    for track in hub['tracks']:
        trackUrl = track['coverage']
        outputDir = '%s%s/' % (sc.defaultDir, track['name'])

        # Call to generateModels will need to be done in a slurm fashion
        if sc.useSlurm:
            # TODO: Implement using slurm
            print("Using Slurm")
        else:
            if sc.multithread:
                gmArgs = (trackUrl, problemsPath, outputDir)
                gmThread = threading.Thread(target=gm.generateModels, args=gmArgs)
                gmThread.start()
            else:
                gm.generateModels(trackUrl, problemsPath, outputDir)


def getProblems(hub):

    genomePath = hub['genomePath']

    genome = genomePath.split('/', 1)[-1]

    genomeDataPath = '%s%s/' % (sc.defaultDir, genome)

    if not os.path.exists(genomeDataPath):
        try:
            os.makedirs(genomeDataPath)
        except OSError:
            return

    problemsFilePath = '%sproblems.bed' % genomeDataPath

    problemsUrl = '%s/%s/problems.bed' % (sc.remoteServer, genomePath)

    # Download problems file for storage
    if not os.path.exists(problemsFilePath):
        with requests.get(problemsUrl) as r:
            with open(problemsFilePath, 'wb') as f:
                f.write(r.content)

    return problemsFilePath


def main():
    startOperation()


if __name__ == '__main__':
    main()
