import os
import sys
import requests
import configparser


def startOperation(remoteServer, useSlurm, location, modelOutput):
    query = {'command': 'getJob', 'args': {}}

    output = requests.post(remoteServer, json=query)

    print(output)


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
        config['slurm']['modelOutput'] = ''
        save = True

    # If a section was missing, save that to the config
    if save:
        with open(configFile, 'w') as cfg:
            config.write(cfg)

    peakLearnerWebserver = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])
    useSlurm = config['slurm']['useSlurm'] == 'true'
    location = config['slurm']['filesLocation']
    modelOutput = config['slurm']['modelOutput']

    startOperation(peakLearnerWebserver, useSlurm, location, modelOutput)


if __name__ == '__main__':
    main()
