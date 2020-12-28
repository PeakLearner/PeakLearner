import configparser

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
jbrowsePath = config['http']['path']

dataPath = config['data']['path']


def testing():
    global test, geneUrl
    test = True
    geneUrl = 'https://rcdata.nau.edu/genomic-ml/PeakLearner/files/'
