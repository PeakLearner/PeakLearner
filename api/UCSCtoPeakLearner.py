import os
import tempfile
import requests
import gzip
import api.PLConfig as cfg
import api.generateProblems as gp


# All this should probably be done asynchronously
def convert(data):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    hub = data['hub']
    # Needs someway to configure this
    dataPath = cfg.dataPath

    path = hub + '/'

    # Initialize Directory
    if not os.path.exists(dataPath + path):
        try:
            os.makedirs(dataPath + path)
        except OSError:
            return

    genomesFile = data['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = genomesFile['genome']

    refSeqPath = downloadGenome(genome, dataPath)

    # Generate problems for this genome
    gp.generateProblems(genome, dataPath)

    createTrackConf(path, dataPath, refSeqPath, genomesFile['trackDb'])

    return dataPath + hub


def createTrackConf(path, dataPath, refSeqPath, tracks):
    trackPath = dataPath + path + 'tracks.conf'
    confFile = []
    superList = []
    trackList = []

    confFile.append('[GENERAL]\n')
    confFile.append('refSeqs=../%s\n\n' % refSeqPath)

    # Load the track list into something which can be converted
    for track in tracks:
        if 'superTrack' in track:
            superList.append(track)
            continue

        if 'parent' in track:
            for super in superList:
                if super['track'] == track['parent']:
                    trackList.append(track)
                    continue
            for parent in trackList:
                if parent['track'] == track['parent']:
                    if 'children' not in parent:
                        parent['children'] = []
                        parent['children'].append(track)
                    else:
                        parent['children'].append(track)

    # TODO: Add gene tracks here

    # Output track list into tracks.conf format
    for track in trackList:
        confFile.append('[tracks.%s]\n' % track['track'])
        confFile.append('key=%s\n' % track['shortLabel'])
        confFile.append('type=InteractivePeakAnnotator/View/Track/MultiXYPlot\n')

        coverage = peaks = None
        for child in track['children']:
            file = child['bigDataUrl'].rsplit('/', 1)
            if 'coverage' in file[1]:
                coverage = child
            else:
                peaks = child

        if coverage is not None:
            confFile.append(
                'urlTemplates+=json:{"url":"%s", "name":"%s", "color": "#235"}\n'
                % (coverage['bigDataUrl'], coverage['shortLabel']))
        if peaks is not None:
            # Probably needs a way to configure baseUrl
            outputStr = 'urlTemplates+=json:{"storeClass": "JBrowse/Store/SeqFeature/REST",' \
                        ' "baseUrl":"http://127.0.0.1:5000",' \
                        ' "name": "%s",' \
                        ' "color": "red",' \
                        ' "lineWidth": 5,' \
                        ' "noCache": true,' \
                        ' "query": {"name": "%s%s"}}\n' % (peaks['shortLabel'], path, track['track'])
            # confFile.append(outputStr)

        confFile.append('storeClass=MultiBigWig/Store/SeqFeature/MultiBigWig\n')
        # Needs some way to specify default baseUrl
        confFile.append('storeConf=json:{"storeClass": "PeakLearnerBackend/Store/SeqFeature/Features"}\n')
        confFile.append('\n')

    with open(trackPath, 'w') as conf:
        conf.writelines(confFile)


def downloadGenome(genome, path):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomePath = 'genomes/' + genome + '/'

    if not os.path.exists(path + genomePath):
        try:
            os.makedirs(path + genomePath)
        except OSError:
            return

    genomeUrl = ucscUrl + genome + '/bigZips/' + genome + '.fa.gz'
    genomeFaPath = genomePath + genome + '.fa'
    genomeFaiPath = genomeFaPath + '.fai'

    if not os.path.exists(path + genomeFaiPath):
        if not os.path.exists(path + genomeFaPath):
            with tempfile.NamedTemporaryFile(suffix='.fa.gz') as temp:
                # Gets FASTA file for genome
                with requests.get(genomeUrl, allow_redirects=True) as r:
                    temp.write(r.content)
                    temp.flush()
                    temp.seek(0)
                with gzip.GzipFile(fileobj=temp, mode='r') as gz:
                    # uncompress the flatfile
                    with open(path + genomeFaPath, 'w+b') as faFile:
                        # Save to file
                        faFile.write(gz.read())

        # Run samtools faidx {genome Fasta File}, creating an indexed Fasta file
        os.system('samtools faidx %s' % path + genomeFaPath)

        # Normal Fasta file no longer needed
        os.remove(path + genomeFaPath)

    return genomeFaiPath
