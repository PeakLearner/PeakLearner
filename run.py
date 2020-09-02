import configparser
import threading
from api import httpServer, restAPI


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

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

# get ports from config
httpServerPort = int(config['http']['port'])
httpServerPath = config['http']['path']

httpArgs = (httpServerPort, httpServerPath)

# start servers
httpServer = threading.Thread(target=httpServer.httpserver, args=httpArgs)
restServer = threading.Thread(target=restAPI.app.run)


def startServer():
    httpServer.start()
    restServer.start()


def joinServer():
    httpServer.join()
    restServer.join()


try:
    startServer()
except KeyboardInterrupt:
    joinServer()
