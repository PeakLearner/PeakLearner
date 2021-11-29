import configparser
import os

minScale = 0.5
gridSearchSize = 10
stopScaling = 1
test = False
geneUrl = 'https://hgdownload.soe.ucsc.edu/goldenPath/'


configFile = 'PeakLearner.cfg'

config = configparser.ConfigParser()
config.read(configFile)

configSections = config.sections()

save = False

# Setup a default config if doesn't exist
if 'http' not in configSections:
    config.add_section('http')
    config['http']['client_id'] = 'google_client_id'
    config['http']['client_secret'] = 'google_client_secret'
    config['http']['auth_redirect'] = 'http://localhost:8080/auth'

    save = True

if 'learning' not in configSections:
    config.add_section('learning')
    config['learning']['doIdlePredictions'] = 'False'
    config['learning']['timeBetween'] = '600'
    config['learning']['numChanges'] = '10'
    config['learning']['minLabeledRegions'] = '20'

    save = True

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

# get ports from config
jbrowsePath = 'jbrowse/jbrowse/'
dataPath = os.path.join(jbrowsePath, 'data/')

timeBetween = int(config['learning']['timeBetween'])
numChanges = int(config['learning']['numChanges'])
minLabeledRegions = int(config['learning']['minLabeledRegions'])
doIdlePredictions = config['learning']['doIdlePredictions'].lower() == 'true'
timeUntilRestart = 3600
client_id = config['http']['client_id']
client_secret = config['http']['client_secret']
authRedirect = config['http']['auth_redirect']



def testing():
    global test, geneUrl, maxJobsToSpawn
    test = True
    geneUrl = 'https://rcdata.nau.edu/genomic-ml/PeakLearner/files/'
    maxJobsToSpawn = 2
