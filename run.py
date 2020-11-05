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

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

# get ports from config
httpServerPort = int(config['http']['port'])
httpServerPath = config['http']['path']

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
