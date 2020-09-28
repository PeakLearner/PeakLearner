import os
import sys
import json
import requests
import configparser

remoteServer = defaultDir = ''
useSlurm = False


def startOperation():
    query = {'command': 'getJob', 'args': {}}

    # TODO: Add error handling
    job = requests.post(remoteServer, json=query)

    if job.status_code == 204:
        return

    # Initialize Directory
    if not os.path.exists(defaultDir):
        try:
            os.makedirs(defaultDir)
        except OSError:
            return

    if job.status_code == 200:
        jobInfo = job.json()
        jobData = jobInfo['data']

        # Reset just loaded val, testing purposes only
        reset = {'command': 'updateJob', 'args': {'id': jobInfo['id'], 'status': 'new'}}
        requests.post(remoteServer, json=reset)

        if 'hub' in jobData:
            newHub(jobData)
        else:
            labelUpdate(jobData)


def labelUpdate(data):
    configFile = '%shub.cfg' % defaultDir
    config = configparser.ConfigParser()
    config.read(configFile)

    genome = config['general']['genome']

    data['genome'] = genome

    problemQuery = {'command': 'getProblems', 'args': data}

    problemReq = requests.post(remoteServer, json=problemQuery)

    # Maybe add some sort of feedback saying label is outside of a problem region
    if problemReq.status_code == 204:
        return

    problems = problemReq.json()

    # TODO: Do something with the label being updated, and the problem area (contig) related to that label

    print("Label Update", problems, data)


def newHub(data):

    newDataFolder = '%s%s/' % (defaultDir, data['hub'])

    if not os.path.exists(newDataFolder):
        try:
            os.makedirs(newDataFolder)
        except OSError:
            return

    genomesFile = data['genomesFile']

    # If multiple genomes, this will not work
    genome = genomesFile['genome']

    newHubConfig(genome)


def newHubConfig(genome):
    configFile = '%shub.cfg' % defaultDir
    config = configparser.ConfigParser()
    config.read(configFile)
    configSections = config.sections()

    save = False

    if 'general' not in configSections:
        config.add_section('general')
        config['general']['genome'] = genome

        save = True

    if save:
        with open(configFile, 'w') as cfg:
            config.write(cfg)


def main():
    global remoteServer, useSlurm, defaultDir
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

    startOperation()


if __name__ == '__main__':
    main()
