import os
import sys
import json
import requests
import configparser
import commands.GenerateModels as gm

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
            labelUpdate(jobData)


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

    # Hub specific config, don't need this to be globally
    config = newHubConfig(data)

    problems = saveProblems(config)

    # Start model generation for each track
    for track in config['tracks']:
        coverage_url = config['tracks'][track]

        trackFolder = '%s%s/' % (newDataFolder, track)

        preprocessTrackModels(coverage_url, problems, trackFolder)


def preprocessTrackModels(coverage, problems, output):

    # TODO: thread this
    if not useSlurm:
        gm.generateModels(coverage, problems, output)
    else:
        # TODO: Convert this to an actual slurm job
        # https://vsoch.github.io/lessons/sherlock-jobs/#python-submission
        os.system('python3 commands/GenerateModels.py %s %s %s' % (coverage, problems, output))


def saveProblems(config):
    genome = config['general']['genome']

    rel_path = 'genomes/%s/problems.bed' % genome

    url = '%s/%s%s' % (remoteServer, remoteDataDir, rel_path)

    localPath = '%s%s' % (defaultDir, rel_path)

    if os.path.exists(localPath):
        return localPath

    file = requests.get(url, allow_redirects=True)

    if file.status_code == 204:
        print("No Genomes File with that Url")
        return

    open(localPath, 'wb').write(file.content)

    return localPath


def newHubConfig(data):
    genomesFile = data['genomesFile']
    genome = genomesFile['genome']
    tracks = genomesFile['trackDb']
    configFile = '%s%s/hub.cfg' % (defaultDir, data['hub'])
    config = configparser.ConfigParser()
    # Allows for uppercase keys
    config.optionxform = str
    config.read(configFile)
    configSections = config.sections()

    save = False

    if 'general' not in configSections:
        config.add_section('general')
        config['general']['genome'] = genome

        save = True

    if 'tracks' not in configSections:
        config.add_section('tracks')

        superList = []
        trackList = []

        # Load the track list into something which can be converted
        for track in tracks:
            # Load super tracks so we can eliminate them
            if 'superTrack' in track:
                superList.append(track)
                continue

            # Python is pass by reference, so trackDb from JobHandler on web server already has children
            if 'parent' in track:
                for super in superList:
                    if super['track'] == track['parent']:
                        trackList.append(track)
                        continue

        for track in trackList:
            name = track['track']
            for child in track['children']:
                file = child['bigDataUrl']
                if 'coverage' in file:
                    config['tracks'][name] = file

        save = True

    if save:
        with open(configFile, 'w') as cfg:
            config.write(cfg)

    return config


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
