#!/usr/bin/python

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

if 'rest' not in configSections:
    config.add_section('rest')
    config['rest']['port'] = '5000'
    config['rest']['path'] = 'jbrowse/'

    save = True

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

#get ports from config
httpServerPort = int(config['http']['port'])
httpServerPath = config['http']['path']
restServerPort = int(config['rest']['port'])
restServerPath = config['rest']['path']

#start servers
httpServer = threading.Thread(target=httpServer.httpserver, args=(httpServerPort, (httpServerPath, )))
restServer = threading.Thread(target=restAPI.app.run)

try:
    httpServer.start()
    restServer.start()

except KeyboardInterrupt:
    httpServer.join()
    restServer.join()
