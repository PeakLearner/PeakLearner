import os
import sys
import requests
import configparser


def startOperation(remoteServer, useSlurm, directory):
    query = {'command': 'getJob', 'args': {}}

    # TODO: Add error handling
    job = requests.post(remoteServer, json=query)

    if job.status_code == 204:
        return

    # Initialize Directory
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError:
            return

    if job.status_code == 200:
        jobInfo = job.json()
        jobData = jobInfo['data']

        # Reset just loaded val, testing purposes only
        reset = {'command': 'updateJob', 'args': {'id': jobInfo['id'], 'status': 'new'}}
        requests.post(remoteServer, json=reset)

        if 'hub' in jobData:
            newHub(jobData, directory)
        else:
            labelUpdate(jobData, useSlurm, directory)


def labelUpdate(data, useSlurm, directory):
    print("Label Update", data)


def newHub(data, directory):

    newDataFolder = '%s%s/' % (directory, data['hub'])

    if not os.path.exists(newDataFolder):
        try:
            os.makedirs(newDataFolder)
        except OSError:
            return

    genomesFile = data['genomesFile']

    # If multiple genomes, this will not work
    genome = genomesFile['genome']

    newHubConfig(newDataFolder, genome)


def newHubConfig(directory, genome):
    configFile = '%shub.cfg' % directory
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

    peakLearnerWebserver = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])
    useSlurm = config['slurm']['useSlurm'] == 'true'
    directory = config['slurm']['filesLocation']

    startOperation(peakLearnerWebserver, useSlurm, directory)


if __name__ == '__main__':
    main()
