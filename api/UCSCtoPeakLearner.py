import os
import tempfile
import requests
import gzip


# All this should probably be done asynchronously
def convert(data):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    hub = data['hub']
    # Needs someway to configure this
    defaultDir = 'data/'

    # Additional user path probably needs to be added here
    dataPath = os.getcwd() + '/' + defaultDir
    path = dataPath + hub + '/'

    # Initialize Directory
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            return

    genomesFile = data['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = genomesFile['genome']

    refSeqPath = downloadGenome(genome, dataPath)

    createConf(path, refSeqPath, genomesFile['trackDb'])


def createConf(path, refSeqPath, tracks):
    trackPath = path + 'tracks.conf'
    confFile = []

    confFile.append('[GENERAL]\n')
    confFile.append('refSeqs=%s\n\n' % refSeqPath)

    for track in tracks:
        print(track)

    with open(trackPath, 'w') as conf:
        conf.writelines(confFile)


def downloadGenome(genome, path):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomePath = path + '/genomes/' + genome + '/'

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            return

    genomeUrl = ucscUrl + genome + '/bigZips/' + genome + '.fa.gz'
    genomeFaPath = genomePath + genome + '.fa'
    genomeFaiPath = genomeFaPath + '.fai'

    if not os.path.exists(genomeFaiPath):
        if not os.path.exists(genomeFaPath):
            with tempfile.NamedTemporaryFile(suffix='.fa.gz') as temp:
                # Gets FASTA file for genome
                with requests.get(genomeUrl, allow_redirects=True) as r:
                    temp.write(r.content)
                    temp.flush()
                    temp.seek(0)
                with gzip.GzipFile(fileobj=temp, mode='r') as gz:
                    # uncompress the flatfile
                    with open(genomeFaPath, 'w+b') as faFile:
                        # Save to file
                        faFile.write(gz.read())

        # Run samtools faidx {genome Fasta File}, creating an indexed Fasta file
        os.system('samtools faidx %s' % genomeFaPath)

        # Normal Fasta file no longer needed
        os.remove(genomeFaPath)

    return genomeFaiPath
