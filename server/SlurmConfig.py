import configparser

configFile = 'PeakLearnerSlurm.cfg'

config = configparser.ConfigParser()
config.optionxform = str
config.read(configFile)

configSections = config.sections()

save = False

if 'general' not in configSections:
    config.add_section('general')
    config['general']['useSlurm'] = 'True'
    config['general']['useCron'] = 'False'
    config['general']['debug'] = 'False'
    config['general']['multithread'] = 'False'

# Setup a default config if doesn't exist
if 'remoteServer' not in configSections:
    config.add_section('remoteServer')
    config['remoteServer']['url'] = 'http://127.0.0.1'
    config['remoteServer']['port'] = '8081'
    config['remoteServer']['dataPath'] = 'data/'
    save = True

if 'slurm' not in configSections:
    config.add_section('slurm')
    config['slurm']['dataPath'] = 'data/'
    config['slurm']['maxJobLen'] = '10'
    config['slurm']['username'] = 'slurmUser'
    config['slurm']['anaconda3venvPath'] = '/'
    config['slurm']['monsoon'] = 'False'
    config['slurm']['maxCPUsPerJob'] = '2'

    save = True

if 'cron' not in configSections:
    config.add_section('cron')
    config['cron']['timeToRun'] = '60'

# If a section was missing, save that to the config
if save:
    with open(configFile, 'w') as cfg:
        config.write(cfg)

remoteServer = "%s:%s" % (config['remoteServer']['url'], config['remoteServer']['port'])
useSlurm = config['general']['useSlurm'].lower() == 'true'
useCron = config['general']['useCron'].lower() == 'true'
debug = config['general']['debug'].lower() == 'true'
multithread = config['general']['multithread'].lower() == 'true'
dataPath = config['slurm']['dataPath']
remoteDataPath = config['remoteServer']['dataPath']
maxJobLen = int(config['slurm']['maxJobLen'])
slurmUser = config['slurm']['username']
condaVenvPath = config['slurm']['anaconda3venvPath']
monsoon = config['slurm']['monsoon'].lower() == 'true'
maxCPUsPerJob = int(config['slurm']['maxCPUsPerJob'])
timeToRun = int(config['cron']['timeToRun'])
