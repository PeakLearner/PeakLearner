import os
import tempfile
import requests
import threading
import gzip
import json
import api.PLConfig as cfg
import api.generateProblems as gp


# All this should probably be done asynchronously
def convert(data):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    hub = data['hub']
    # Needs someway to configure this
    dataPath = cfg.dataPath

    hubPath = os.path.join(dataPath, hub)

    # Initialize Directory
    if not os.path.exists(hubPath):
        try:
            os.makedirs(hubPath)
        except OSError:
            return

    genomesFile = data['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = genomesFile['genome']

    threads = []

    includes = getGeneTracks(genome, dataPath, threads)

    # Generate problems for this genome
    problems = gp.generateProblems(genome, dataPath)

    problemPath = generateProblemTrack(problems)

    includes.append(problemPath)

    refSeqPath = getRefSeq(genome, dataPath, includes, threads)

    createTrackListJson(hubPath, hub, refSeqPath, genomesFile['trackDb'])

    for thread in threads:
        thread.join()

    # Removing last character as having the / at the end breaks trackList includes
    return hubPath


def createTrackListJson(path, hub, refSeqPath, tracks):
    # Include here provides the required assembly, as well as generated genes
    config = {'include': ['../%s' % refSeqPath], 'tracks': []}

    superList = []
    trackList = []

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

    for track in trackList:
        trackFile = {'label': "%s/%s" % (hub, track['track']), 'key': track['shortLabel'],
                     'type': 'InteractivePeakAnnotator/View/Track/MultiXYPlot',
                     'urlTemplates': []}

        categories = 'Data'
        for category in track['longLabel'].split(' | ')[:-1]:
            categories = categories + ' / %s' % category

        trackFile['category'] = categories

        # Determine which track is the coverage data
        coverage = peaks = None
        for child in track['children']:
            file = child['bigDataUrl'].rsplit('/', 1)
            if 'coverage' in file[1]:
                coverage = child
            if 'joint_peaks' in file[1]:
                peaks = child

        # Add Data Url to config
        if coverage is not None:
            trackFile['urlTemplates'].append(
                {'url': coverage['bigDataUrl'], 'name': '%s/%s' % (hub, coverage['shortLabel']), 'color': '#235'}
            )

        if peaks is not None:
            trackFile['urlTemplates'].append(
                {'storeClass': 'PeakLearnerBackend/Store/SeqFeature/Model', 'name': '%s/%s' % (hub, peaks['shortLabel']),
                 'color': 'red', 'lineWidth': 5}
            )

        trackFile['storeClass'] = 'MultiBigWig/Store/SeqFeature/MultiBigWig'
        trackFile['storeConf'] = {'storeClass': 'PeakLearnerBackend/Store/SeqFeature/Labels'}

        config['tracks'].append(trackFile)

    trackPath = os.path.join(path, 'trackList.json')

    with open(trackPath, 'w') as conf:
        json.dump(config, conf)


def getRefSeq(genome, path, includes, threads):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomeRelPath = os.path.join('genomes', genome)

    genomePath = os.path.join(path, genomeRelPath)

    includes = formatIncludes(includes, genomePath)

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            return

    genomeUrl = ucscUrl + genome + '/bigZips/' + genome + '.fa.gz'
    genomeFaPath = os.path.join(genomePath, genome + '.fa')
    genomeFaiPath = genomeFaPath + '.fai'

    dlThread = threading.Thread(target=downloadRefSeq, args=(genomeUrl, genomeFaPath, genomeFaiPath))
    threads.append(dlThread)
    dlThread.start()

    genomeConfigPath = os.path.join(genomePath, 'trackList.json')

    with open(genomeConfigPath, 'w') as genomeCfg:
        genomeFile = genome + '.fa.fai'
        output = {'refSeqs': genomeFile, 'include': includes}
        json.dump(output, genomeCfg)

    genomeConfigRelPath = os.path.join(genomeRelPath, 'trackList.json')

    return genomeConfigRelPath


def downloadRefSeq(genomeUrl, genomeFaPath, genomeFaiPath):
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

        print("Samtools")

        # Run samtools faidx {genome Fasta File}, creating an indexed Fasta file
        os.system('samtools faidx %s' % genomeFaPath)

        # Normal Fasta file no longer needed
        os.remove(genomeFaPath)


def getGeneTracks(genome, path, threads):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomePath = '%sgenomes/%s/' % (path, genome)

    genesPath = '%sgenes/' % genomePath

    if not os.path.exists(genesPath):
        try:
            os.makedirs(genesPath)
        except OSError:
            return

    genesUrl = "%s%s/database/" % (ucscUrl, genome)

    genes = ['ensGene', 'knownGene', 'ncbiRefSeq', 'refGene', 'ccdsGene']

    getDbFiles('trackDb', genesUrl, genesPath)

    includes = []

    for gene in genes:
        geneTrackPath = '%s%s/' % (genomePath, gene)

        geneArgs = (gene, genesUrl, genesPath, geneTrackPath)

        geneThread = threading.Thread(target=getAndProcessGeneTrack, args=geneArgs)
        threads.append(geneThread)
        geneThread.start()

        includes.append(os.path.join(geneTrackPath, 'trackList.json'))

    return includes


def getAndProcessGeneTrack(gene, genesUrl, genesPath, geneTrackPath):
    getDbFiles(gene, genesUrl, genesPath)

    if not os.path.exists(geneTrackPath):
        try:
            os.makedirs(geneTrackPath)
        except OSError:
            return

        generateTrack = "bin/ucsc-to-json.pl -q --in %s --out %s --track %s" % (genesPath, geneTrackPath, gene)

        # This will use Jbrowse perl files to generate a track for that specific gene
        os.system(generateTrack)

        addGeneCategory(geneTrackPath, 'Reference / Genes')


def generateProblemTrack(path):
    trackFolder = '%s/' % path.rsplit('.', 1)[0]

    if not os.path.exists(trackFolder):
        try:
            os.makedirs(trackFolder)
        except OSError:
            return

        command = 'bin/flatfile-to-json.pl --bed %s --out %s --trackLabel Problems' % (path, trackFolder)

        # Will generate a jbrowse track using the problems.bed flatfile
        os.system(command)

        addGeneCategory(trackFolder, 'Reference')

    return '%strackList.json' % trackFolder


def getDbFiles(name, url, output):
    files = ['%s.txt.gz' % name, '%s.sql' % name]

    for file in files:
        if not os.path.exists(output + file):
            with requests.get(url + file, allow_redirects=True) as r:
                open(output + file, 'w+b').write(r.content)


# TODO: Remove lock and move this to DB
geneLock = threading.Lock()


def addGeneCategory(genePath, label):
    confFile = '%strackList.json' % genePath

    geneLock.acquire()

    conf = json.loads(open(confFile, 'r').read())

    # Only one track in these confs
    if 'category' not in conf['tracks'][0]:
        conf['tracks'][0]['category'] = label

    with open(confFile, 'w') as newConfFile:
        json.dump(conf, newConfFile)

    geneLock.release()


def formatIncludes(includes, prePath):
    output = []

    for include in includes:
        output.append(os.path.relpath(include, start=prePath))

    return output
