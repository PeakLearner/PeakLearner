import os
import configparser

configFile = 'PeakLearnerSlurm.cfg'

config = configparser.ConfigParser()
config.optionxform = str
config.read(configFile)

configSections = config.sections()

save = False

if 'general' not in configSections:
    config.add_section('general')
    config['general']['debug'] = 'False'
    config['general']['numWorkers'] = str(1)
    save = True


# Setup a default config if doesn't exist
if 'remoteServer' not in configSections:
    config.add_section('remoteServer')
    config['remoteServer']['url'] = 'https://peaklearner.rc.nau.edu'
    config['remoteServer']['port'] = '80'
    config['remoteServer']['verify'] = 'True'
    save = True

if 'slurm' not in configSections:
    config.add_section('slurm')
    config['slurm']['dataPath'] = 'slurmdata/'
    save = True

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

port = int(config['remoteServer']['port'])

if port == 80:
    remoteServer = "%s" % config['remoteServer']['url']
else:
    remoteServer = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])

verify = config['remoteServer']['verify'].lower() == 'true'
debug = config['general']['debug'].lower() == 'true'
dataPath = config['slurm']['dataPath']
jobUrl = os.path.join(remoteServer, 'Jobs')
numWorkers = int(config['general']['numWorkers'])


def testing():
    global remoteServer, jobUrl
    remoteServer = 'http://localhost:8080'
    jobUrl = os.path.join(remoteServer, 'Jobs')
