import os
import requests
import threading
import json
import api.PLConfig as cfg
import api.generateProblems as gp


# All this should probably be done asynchronously
def convert(data, user=1):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    hub = data['hub']
    genomesFile = data['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = genomesFile['genome']

    dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

    includes = getGeneTracks(genome, dataPath)

    # Generate problems for this genome
    problems = gp.generateProblems(genome, dataPath)

    problemPath = generateProblemTrack(problems)

    includes.append(problemPath)

    refSeqPath = getRefSeq(genome, dataPath, includes)

    outputPath = createTrackListJson(hub, dataPath, refSeqPath, genomesFile['trackDb'])

    return outputPath


def createTrackListJson(hub, dataPath, refSeqPath, tracks):
    hubPath = os.path.join(dataPath, hub)

    if not os.path.exists(hubPath):
        try:
            os.makedirs(hubPath)
        except OSError:
            return

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

    trackPath = os.path.join(hubPath, 'trackList.json')

    with open(trackPath, 'w') as conf:
        json.dump(config, conf)

    # TODO: maybe add user ID to this if not eventually just storing trackLists?
    return os.path.join(cfg.dataPath, hub)


def getRefSeq(genome, path, includes):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomeRelPath = os.path.join('genomes', genome)

    genomePath = os.path.join(path, genomeRelPath)

    includes = formatIncludes(includes, genomePath)

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            print(genomePath, "does not exist")
            return

    genomeUrl = ucscUrl + genome + '/bigZips/' + genome + '.fa.gz'
    genomeFaPath = os.path.join(genomePath, genome + '.fa')
    genomeFaiPath = genomeFaPath + '.fai'

    downloadRefSeq(genomeUrl, genomeFaPath, genomeFaiPath)

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
            with open(genomeFaPath + '.gz', 'wb') as temp:
                # Gets FASTA file for genome
                with requests.get(genomeUrl, allow_redirects=True) as r:
                    temp.write(r.content)
                    temp.flush()
                    temp.seek(0)

            os.system('gzip -d %s' % genomeFaPath + '.gz')

        print("Samtools on", genomeFaPath)

        # Run samtools faidx {genome Fasta File}, creating an indexed Fasta file
        os.system('samtools faidx %s' % genomeFaPath)


def getGeneTracks(genome, dataPath):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/'

    genomePath = os.path.join(dataPath, 'genomes', genome)

    genesPath = os.path.join(genomePath, 'genes')

    if not os.path.exists(genesPath):
        try:
            os.makedirs(genesPath)
        except OSError:
            return

    genesUrl = "%s%s/database/" % (ucscUrl, genome)

    genes = ['ensGene', 'knownGene', 'ncbiRefSeq', 'refGene', 'ccdsGene']

    getDbFiles('trackDb', genesUrl, genesPath)

    includes = []

    geneThreads = []

    for gene in genes:
        geneTrackPath = os.path.join(genomePath, gene)

        args = (gene, genesUrl, genesPath, geneTrackPath)

        geneThread = threading.Thread(target=getAndProcessGeneTrack, args=args)
        geneThreads.append(geneThread)
        geneThread.start()

        includes.append(os.path.join(geneTrackPath, 'trackList.json'))

    for thread in geneThreads:
        thread.join()

    return includes


def getAndProcessGeneTrack(gene, genesUrl, genesPath, geneTrackPath):
    getDbFiles(gene, genesUrl, genesPath)

    trackListPath = os.path.join(geneTrackPath)

    if not os.path.exists(geneTrackPath):
        try:
            os.makedirs(geneTrackPath)
        except OSError:
            return

    if not os.path.exists(trackListPath):
        command = os.path.join(cfg.jbrowsePath, 'bin', 'ucsc-to-json.pl')

        generateTrack = "%s -q --in %s --out %s --track %s" % (command, genesPath, geneTrackPath, gene)

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

        command = os.path.join(cfg.jbrowsePath, 'bin', 'flatfile-to-json.pl')

        generateTrack = '%s --bed %s --out %s --trackLabel Problems' % (command, path, trackFolder)

        # Will generate a jbrowse track using the problems.bed flatfile
        os.system(generateTrack)

        addGeneCategory(trackFolder, 'Reference')

    return os.path.join(trackFolder, 'trackList.json')


def getDbFiles(name, url, output):
    files = ['%s.txt.gz' % name, '%s.sql' % name]

    for file in files:
        path = os.path.join(output, file)
        if not os.path.exists(path):
            with requests.get(url + file, allow_redirects=True) as r:
                if not r.status_code == 200:
                    print("getDbFile Error", r.status_code)
                with open(path, 'wb') as f:
                    f.write(r.content)


def addGeneCategory(genePath, label):
    confFile = os.path.join(genePath, 'trackList.json')

    conf = json.loads(open(confFile, 'r').read())

    # Only one track in these confs
    if 'category' not in conf['tracks'][0]:
        conf['tracks'][0]['category'] = label

    with open(confFile, 'w') as newConfFile:
        json.dump(conf, newConfFile)


def formatIncludes(includes, prePath):
    output = []

    for include in includes:
        output.append(os.path.relpath(include, start=prePath))

    return output
