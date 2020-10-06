import os
import sys
import json
import requests
import configparser

remoteServer = remoteDataDir = defaultDir = ''
useSlurm = False


def startOperation():
    # TODO: Multiple jobs per run (If taking the route of cron jobs)
    query = {'command': 'getJob', 'args': {}}

    # TODO: Add error handling
    job = requests.post(remoteServer, json=query)

    # No jobs available
    if job.status_code == 204:
        return

    # Initialize Directory
    if not os.path.exists(defaultDir):
        try:
            os.makedirs(defaultDir)
        except OSError:
            return

    checkForBigWigToBedGraph()

    if job.status_code == 200:
        jobInfo = job.json()
        jobData = jobInfo['data']

        # Reset just loaded val, testing purposes only
        reset = {'command': 'updateJob', 'args': {'id': jobInfo['id'], 'status': 'New'}}
        requests.post(remoteServer, json=reset)

        if 'hub' in jobData:
            newHub(jobData)
        else:
            newModel(jobData)


def checkForBigWigToBedGraph():
    # Initialize Directory
    scriptDir = 'bin/'

    if not os.path.exists(scriptDir):
        try:
            os.makedirs(scriptDir)
        except OSError:
            return

    bigWigScript = '%s%s' % (scriptDir, 'bigWigToBedGraph')

    if not os.path.exists(bigWigScript):
        bigWigToBedGraphUrl = 'http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bigWigToBedGraph'

        r = requests.get(bigWigToBedGraphUrl, allow_redirects=True)

        if r.status_code == 200:
            open(bigWigScript, 'wb').write(r.content)


def newModel(data):
    print(data)


def newHub(data):

    newDataFolder = '%s%s/' % (defaultDir, data['hub'])

    if not os.path.exists(newDataFolder):
        try:
            os.makedirs(newDataFolder)
        except OSError:
            return

    hubInfoArgs = {'command': 'getHubInfo', 'args': {'hub': data['hub']}}

    hubRequest = requests.post(remoteServer, json=hubInfoArgs)

    if not hubRequest.status_code == 200:
        return

    hub = hubRequest.json()

    problemsPath = getProblems(hub)

    # TODO: Preliminary Model Generation


def getProblems(hub):

    genomePath = hub['genomePath']

    genome = genomePath.split('/', 1)[-1]

    genomeDataPath = '%s%s/' % (defaultDir, genome)

    if not os.path.exists(genomeDataPath):
        try:
            os.makedirs(genomeDataPath)
        except OSError:
            return

    problemsFilePath = '%sproblems.bed' % genomeDataPath

    problemsUrl = '%s/%s/problems.bed' % (remoteServer, genomePath)

    # Download problems file for storage
    if not os.path.exists(problemsFilePath):
        with requests.get(problemsUrl) as r:
            with open(problemsFilePath, 'wb') as f:
                f.write(r.content)

    return problemsFilePath


def main():
    global remoteServer, remoteDataDir, useSlurm, defaultDir
    configFile = 'PeakLearnerSlurm.cfg'

    config = configparser.ConfigParser()
    config.read(configFile)

    configSections = config.sections()

    save = False

    # Setup a default config if doesn't exist
    if 'remoteServer' not in configSections:
        config.add_section('remoteServer')
        config['remoteServer']['url'] = 'http://127.0.0.1'
        config['remoteServer']['port'] = '8081'
        config['remoteServer']['dataDir'] = 'data/'
        save = True

    if 'slurm' not in configSections:
        config.add_section('slurm')
        config['slurm']['useSlurm'] = 'true'
        config['slurm']['filesLocation'] = 'data/'

        save = True

    # If a section was missing, save that to the config
    if save:
        with open(configFile, 'w') as cfg:
            config.write(cfg)

    remoteServer = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])
    useSlurm = config['slurm']['useSlurm'] == 'true'
    defaultDir = config['slurm']['filesLocation']
    remoteDataDir = config['remoteServer']['dataDir']

    startOperation()


if __name__ == '__main__':
    main()
