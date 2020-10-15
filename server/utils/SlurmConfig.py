import configparser

configFile = 'PeakLearnerSlurm.cfg'

config = configparser.ConfigParser()
config.optionxform = str
config.read(configFile)

configSections = config.sections()

save = False

# Setup a default config if doesn't exist
if 'remoteServer' not in configSections:
    config.add_section('remoteServer')
    config['remoteServer']['url'] = 'http://127.0.0.1'
    config['remoteServer']['port'] = '8081'
    config['remoteServer']['dataPath'] = 'data/'
    save = True

if 'slurm' not in configSections:
    config.add_section('slurm')
    config['slurm']['useSlurm'] = 'True'
    config['slurm']['testing'] = 'False'
    config['slurm']['multithread'] = 'False'
    config['slurm']['dataPath'] = 'data/'

    save = True

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

remoteServer = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])
useSlurm = config['slurm']['useSlurm'].lower() == 'true'
testing = config['slurm']['testing'].lower() == 'true'
multithread = config['slurm']['multithread'].lower() == 'true'
dataPath = config['slurm']['dataPath']
remoteDataPath = config['remoteServer']['dataPath']
