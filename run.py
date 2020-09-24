import configparser
import threading
from api import httpServer, TrackHandler, PLConfig


configFile = 'PeakLearner.cfg'

config = configparser.ConfigParser()
config.read(configFile)

configSections = config.sections()

save = False

# Setup a default config if doesn't exist
if 'http' not in configSections:
    config.add_section('http')
    config['http']['port'] = '8081'
    config['http']['path'] = 'jbrowse/'

    save = True

if 'data' not in configSections:
    config.add_section('data')
    config['data']['path'] = 'data/'

    save = True

if 'slurm' not in configSections:
    config.add_section('slurm')
    config['slurm']['url'] = 'slurm.url'
    config['slurm']['user'] = 'user'
    # TODO: use tokens, passwords are insecure
    config['slurm']['pass'] = 'pass'

    save = True

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

# get ports from config
httpServerPort = int(config['http']['port'])
httpServerPath = config['http']['path']

PLConfig.slurmUrl = config['slurm']['url']
PLConfig.slurmUser = config['slurm']['user']
PLConfig.slurmPass = config['slurm']['pass']
PLConfig.dataPath = config['data']['path']

httpArgs = (httpServerPort, httpServerPath)

# start servers
httpServer = threading.Thread(target=httpServer.httpserver, args=httpArgs)


def startServer():
    httpServer.start()


def joinServer():
    httpServer.join()


try:
    startServer()
except KeyboardInterrupt:
    joinServer()
