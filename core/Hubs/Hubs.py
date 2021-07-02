import os
import json
import gzip
import requests
import tempfile
import threading
import pandas as pd
from core.Jobs import Jobs
from core.Labels import Labels
from core.Models import Models
from core.Handlers import Tracks
from core.Permissions import Permissions
from core.util import PLConfig as cfg, PLdb as db
from simpleBDB import retry, txnAbortOnError, AbortTXNException


@retry
@txnAbortOnError
def getHubJsons(query, handler, txn=None):
    if handler == 'trackList.json':

        hubInfo = db.HubInfo(query['user'], query['hub']).get(txn=txn)

        return createTrackListWithHubInfo(hubInfo, query['user'], query['hub'])
    else:
        print('no handler for %s' % query['handler'])

@retry
@txnAbortOnError
def goToRegion(data, txn=None):
    user = data['user']
    hub = data['hub']

    hubInfo = db.HubInfo(user, hub).get(txn=txn)
    genome = hubInfo['genome']
    problems = db.Problems(genome).get(txn=txn)
    tracks = list(hubInfo['tracks'].keys())
    trackDf = pd.DataFrame(tracks, columns=['track'])
    trackDf['user'] = user
    trackDf['hub'] = hub

    trackProblems = []
    for key, row in trackDf.iterrows():
        grouped = problems.groupby(['chrom'], as_index=False)
        problemLabels = grouped.apply(checkProblemForLabels, row, txn)
        problemLabels['track'] = row['track']
        trackProblems.append(problemLabels)

    trackProblems = pd.concat(trackProblems)

    problemGroups = trackProblems.groupby(['chrom', 'chromStart', 'chromEnd'], as_index=False)

    toCheck = data['type'].lower() == 'labeled'

    regions = problemGroups.apply(checkPossibleRegion)
    regions.columns = ['chrom', 'chromStart', 'chromEnd', 'labeled']

    possibleRegions = regions[regions['labeled'] == toCheck]

    regionToGoTo = possibleRegions.sample()

    region = {
        'ref': regionToGoTo['chrom'].iloc[0],
        'start': regionToGoTo['chromStart'].iloc[0].item(),
        'end': regionToGoTo['chromEnd'].iloc[0].item()
    }

    return region


def checkPossibleRegion(row):
    return row['labeled'].any()


def checkProblemForLabels(chromGroup, track, txn):
    chrom = chromGroup['chrom'].iloc[0]

    key = (track['user'], track['hub'], track['track'], chrom)

    if db.Labels.has_key(key):
        labels = db.Labels(track['user'], track['hub'], track['track'], chrom).get(txn=txn)

        chromGroup['labeled'] = chromGroup.apply(checkLabelsInBoundsOnChrom, axis=1, args=(labels,))

    else:
        chromGroup['labeled'] = False

    return chromGroup


def checkLabelsInBoundsOnChrom(row, labels):
    inBounds = labels.apply(db.checkInBounds, axis=1, args=(row['chrom'], row['chromStart'], row['chromEnd']))
    return inBounds.any()


@retry
@txnAbortOnError
def removeUserFromHub(request, owner, hubName, delUser, txn=None):
    """Removes a user from a hub given the hub name, owner userid, and the userid of the user to be removed
    Adjusts the db.HubInfo object by calling the remove() function on the removed userid from the ['users'] item of the
    db.HubInfo object.
    """

    userid = request.authenticated_userid

    txn = db.getTxn(parent=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn, write=True)

    if not perms.hasPermission(userid, 'Hub'):
        txn.commit()
        return

    del perms.users[delUser]

    permDb.put(perms, txn=txn)
    txn.commit()


@retry
@txnAbortOnError
def addTrack(owner, hubName, userid, category, trackName, url, txn=None):
    hub = db.HubInfo(owner, hubName).get(txn=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn)

    if not perms.hasPermission(userid, 'Hub'):
        raise AbortTXNException

    hub['tracks'][trackName] = {'categories': category, 'key': trackName, 'url': url}
    db.HubInfo(owner, hubName).put(hub, txn=txn)


@retry
@txnAbortOnError
def removeTrack(owner, hubName, userid, trackName, txn=None):
    hub = db.HubInfo(owner, hubName).get(txn=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn)

    if not perms.hasPermission(userid, 'Hub'):
        raise AbortTXNException

    del hub['tracks'][trackName]
    db.HubInfo(owner, hubName).put(hub, txn=txn)


@retry
@txnAbortOnError
def deleteHub(owner, hub, userid, txn=None):
    if userid != owner:
        raise AbortTXNException

    hub_info = None
    db.HubInfo(userid, hub).put(hub_info, txn=txn)


@retry
@txnAbortOnError
def getHubInfosForMyHubs(userid, txn=None):
    hubInfos = {}
    usersdict = {}
    permissions = {}

    cursor = db.HubInfo.getCursor(txn=txn, bulk=True)

    current = cursor.next()
    while current is not None:
        key, currHubInfo = current

        owner = key[0]
        hubName = key[1]

        perms = db.Permission(owner, hubName).get(txn=txn)

        if not perms.hasViewPermission(userid, currHubInfo):
            print('no perm')
            current = cursor.next()
            continue

        permissions[(owner, hubName)] = perms.users

        usersdict[hubName] = perms.groups

        everyLabelKey = db.Labels.keysWhichMatch(owner, hubName)

        num_labels = 0
        for key in everyLabelKey:
            num_labels += len(db.Labels(*key).get(txn=txn).index)

        currHubInfo['numLabels'] = num_labels

        hubInfos[hubName] = currHubInfo

        current = cursor.next()

    cursor.close()

    return {"user": userid,
            "hubInfos": hubInfos,
            "usersdict": usersdict,
            "permissions": permissions}


@retry
@txnAbortOnError
def makeHubPublic(data, txn=None):
    userid = data['currentUser']
    owner = data['user']
    hubName = data['hub']

    if userid != owner:
        perms = db.Permission(owner, hubName).get(txn=txn)
        if not perms.hasPermission(userid, 'Hub'):
            return False

    chkpublic = "chkpublic" in data.keys()
    hub = db.HubInfo(owner, hubName).get(txn=txn, write=True)
    hub['isPublic'] = chkpublic
    db.HubInfo(owner, hubName).put(hub, txn=txn)

    return True


def createTrackListWithHubInfo(info, owner, hub):
    if info is None:
        return
    refSeqPath = os.path.join('genomes', info['genome'], 'trackList.json')

    tracklist = {'include': [refSeqPath], 'tracks': [], 'owner': owner, 'hub': hub}

    tracks = info['tracks']

    for track in tracks.keys():
        trackData = tracks[track]
        trackConf = {'label': track, 'key': trackData['key'], 'type': 'PeakLearnerBackend/View/Track/Model',
                     'showLabels': 'true', 'urlTemplates': [], 'category': trackData['categories']}

        urlTemplate = {'url': trackData['url'], 'name': track, 'color': '#235'}

        trackConf['urlTemplates'].append(urlTemplate)

        trackConf['storeClass'] = 'MultiBigWig/Store/SeqFeature/MultiBigWig'
        trackConf['storeConf'] = {'storeClass': 'PeakLearnerBackend/Store/SeqFeature/Labels',
                                  'modelClass': 'PeakLearnerBackend/Store/SeqFeature/Models'}

        tracklist['tracks'].append(trackConf)

    return tracklist


def parseHub(data):
    parsed = parseUCSC(data)
    # Add a way to configure hub here somehow instead of just loading everythingS
    return createHubFromParse(parsed)


# All this should probably be done asynchronously
def createHubFromParse(parsed):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    hub = parsed['hub']
    user = parsed['user']
    genomesFile = parsed['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = genomesFile['genome']

    hubInfo = {'genome': genome,
               'isPublic': parsed['isPublic'],
               'owner': user}

    dataPath = os.path.join(cfg.jbrowsePath, cfg.dataPath)

    includes = getGeneTracks(genome, dataPath)

    # Generate problems for this genome

    txn = db.getTxn()
    problems = generateProblems(genome, dataPath, txn)
    txn.commit()

    problemPath = generateProblemTrack(problems)

    includes.append(problemPath)

    getRefSeq(genome, dataPath, includes)

    path = storeHubInfo(user, hub, genomesFile['trackDb'], hubInfo, genome)
    Permissions.Permission(user, hub).putNewPermissions()

    return path


def storeHubInfo(user, hub, tracks, hubInfo, genome):
    superList = []
    trackList = []
    hubInfoTracks = {}

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

    txn = db.getTxn()
    for track in trackList:
        # Determine which track is the coverage data
        coverage = None
        for child in track['children']:
            file = child['bigDataUrl'].rsplit('/', 1)
            if 'coverage' in file[1]:
                coverage = child

        # Add Data Url to config
        if coverage is not None:
            categories = 'Data'
            for category in track['longLabel'].split(' | ')[:-1]:
                categories = categories + ' / %s' % category

            hubInfoTracks[track['track']] = {'categories': categories,
                                             'key': track['shortLabel'],
                                             'url': coverage['bigDataUrl']}

            trackTxn = db.getTxn(parent=txn)
            if not checkForPrexistingLabels(coverage['bigDataUrl'], user, hub, track, genome, trackTxn):
                trackTxn.abort()
                continue
            trackTxn.commit()


    hubInfo['tracks'] = hubInfoTracks
    db.HubInfo(user, hub).put(hubInfo, txn=txn)
    txn.commit()
    return '/%s/' % os.path.join(str(user), hub)


def checkForPrexistingLabels(coverageUrl, user, hub, track, genome, txn):
    trackUrl = coverageUrl.rsplit('/', 1)[0]
    labelUrl = '%s/labels.bed' % trackUrl
    with requests.get(labelUrl, verify=False) as r:
        if not r.status_code == 200:
            return False

        with tempfile.TemporaryFile() as f:
            f.write(r.content)
            f.flush()
            f.seek(0)
            labels = pd.read_csv(f, sep='\t', header=None)
            labels.columns = Labels.labelColumns

    grouped = labels.groupby(['chrom'], as_index=False)
    grouped.apply(saveLabelGroup, user, hub, track, genome, coverageUrl, txn)

    return True


def saveLabelGroup(group, user, hub, track, genome, coverageUrl, txn):
    group = group.sort_values('chromStart', ignore_index=True)

    group['annotation'] = group.apply(fixNoPeaks, axis=1)
    chrom = group['chrom'].loc[0]

    txn = db.getTxn()

    numLabels = len(group.index)

    changes = db.Prediction('changes').get(write=True, txn=txn)

    changes = changes + numLabels

    db.Prediction('changes').put(changes, txn=txn)

    db.Labels(user, hub, track['track'], chrom).put(group, txn=txn)

    chromProblems = Tracks.getProblemsForChrom(genome, chrom, txn)

    withLabels = chromProblems.apply(checkIfProblemHasLabels, axis=1, args=(group,))

    doPregen = chromProblems[withLabels]

    submitPregenWithData(doPregen, user, hub, track, numLabels, coverageUrl, txn)

    txn.commit()


def submitPregenWithData(doPregen, user, hub, track, numLabels, coverageUrl, txn):
    recs = doPregen.to_dict('records')
    for problem in recs:
        problemTxn = db.getTxn(parent=txn)
        penalties = Models.peakSegDiskPrePenalties
        job = Jobs.PregenJob(user,
                             hub,
                             track['track'],
                             problem,
                             penalties,
                             numLabels,
                             trackUrl=coverageUrl)

        if job.putNewJob(problemTxn) is None:
            problemTxn.abort()
            continue

        problemTxn.commit()


def checkIfProblemHasLabels(problem, labels):
    inBounds = labels.apply(db.checkInBounds,
                            axis=1,
                            args=(problem['chrom'],
                                  problem['chromStart'],
                                  problem['chromEnd']))

    return inBounds.any()


def fixNoPeaks(row):
    if row['annotation'] == 'noPeaks':
        return 'noPeak'
    return row['annotation']


def getRefSeq(genome, path, includes):
    genomeRelPath = os.path.join('genomes', genome)

    genomePath = os.path.join(path, genomeRelPath)

    includes = formatIncludes(includes, genomePath)

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            print(genomePath, "does not exist")
            return

    genomeUrl = cfg.geneUrl + genome + '/bigZips/' + genome + '.fa.gz'
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
                with requests.get(genomeUrl, allow_redirects=True, verify=False) as r:
                    temp.write(r.content)
                    temp.flush()
                    temp.seek(0)

            os.system('gzip -d %s' % genomeFaPath + '.gz')

        # Run samtools faidx {genome Fasta File}, creating an indexed Fasta file
        os.system('samtools faidx %s' % genomeFaPath)


def getGeneTracks(genome, dataPath):
    genomePath = os.path.join(dataPath, 'genomes', genome)

    genesPath = os.path.join(genomePath, 'genes')

    if not os.path.exists(genesPath):
        try:
            os.makedirs(genesPath)
        except OSError:
            return

    genesUrl = "%s%s/database/" % (cfg.geneUrl, genome)

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

    trackListPath = os.path.join(geneTrackPath, 'trackList.json')

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

        generateTrack = '%s --bed %s --out %s --trackLabel Contigs' % (command, path, trackFolder)

        # Will generate a jbrowse track using the problems.bed flatfile
        os.system(generateTrack)

        addGeneCategory(trackFolder, 'Reference')

    return os.path.join(trackFolder, 'trackList.json')


def getDbFiles(name, url, output):
    files = ['%s.txt.gz' % name, '%s.sql' % name]

    for file in files:
        path = os.path.join(output, file)
        if not os.path.exists(path):
            with requests.get(url + file, allow_redirects=True, verify=False) as r:
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


def parseUCSC(data):
    url = data['url']
    hubReq = requests.get(url, allow_redirects=True, verify=False)
    if not hubReq.status_code == 200:
        return None
    path = ""
    if url.find('/'):
        vals = url.rsplit('/', 1)
        path = vals[0]

    lines = hubReq.text.split('\n')

    hub = readUCSCLines(lines)

    # SETUP HUB VALUE KEYS
    user = data['user']

    if user is None:
        user = 'Public'
        hub['isPublic'] = True
    else:
        hub['isPublic'] = False

    hub['user'] = user
    hub['owner'] = user
    hub['labels'] = 0
    hub['users'] = []

    if hub['genomesFile']:
        hub['genomesFile'] = loadGenomeUCSC(hub, path)

    return hub


def loadGenomeUCSC(hub, path):
    genomeUrl = path + '/' + hub['genomesFile']

    genomeReq = requests.get(genomeUrl, allow_redirects=True, verify=False)

    lines = genomeReq.text.split('\n')

    output = readUCSCLines(lines)

    if output['trackDb'] is not None:
        output['trackDb'] = loadTrackDbUCSC(output, path)

    return output


def loadTrackDbUCSC(genome, path):
    trackUrl = path + '/' + genome['trackDb']

    trackReq = requests.get(trackUrl, allow_redirects=True, verify=False)

    lines = trackReq.text.split('\n')

    return readUCSCLines(lines)


# Reads the lines of the current file
def readUCSCLines(lines):
    output = []
    current = {}

    outputList = False

    start = True

    added = False

    for line in lines:
        line = line.strip()
        if line == "":
            if start:
                start = False
                continue
            else:
                if not added:
                    added = True
                    output.append(current)
                    current = {}
        else:
            # If it gets to this point after adding one, then there are multiple
            if added:
                outputList = True
                added = False
            vals = line.split(" ", 1)

            current[vals[0]] = vals[1]

    if outputList:
        return output
    else:
        return output[0]


def generateProblems(genome, path, txn=None):
    genesUrl = "%s%s/database/" % (cfg.geneUrl, genome)
    genomePath = os.path.join(path, 'genomes', genome)
    outputFile = os.path.join(genomePath, 'problems.bed')

    if db.Problems.has_key(genome):
        return outputFile

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            return

    files = []

    for file in ['chromInfo', 'gap']:
        outputPath = os.path.join(genomePath, file + '.txt')
        fileUrl = genesUrl + file + '.txt.gz'
        files.append(downloadAndUnpackFile(fileUrl, outputPath))

    chromInfo = pd.read_csv(files[0], sep='\t', header=None).iloc[:, 0:2]
    chromInfo.columns = ['chrom', 'bases']

    gap = pd.read_csv(files[1], sep='\t', header=None).iloc[:, 1:4]
    gap.columns = ['chrom', 'gapStart', 'gapEnd']

    join = gap.merge(chromInfo, on='chrom', how='outer')

    nan = join.isnull()['gapStart' and 'gapEnd']
    nonNan = join.notnull()['gapStart' and 'gapEnd']

    nanOutput = join[nan].groupby(['chrom']).apply(createNanProblems)

    nonNanOutput = join[nonNan].groupby(['chrom']).apply(createProblems)

    frames = [nonNanOutput, nanOutput]

    output = pd.concat(frames, sort=False)

    # Removes all entries with an _, not needed because these are genome "Fixes"
    output = output[~output['chrom'].str.contains('_')]

    output['chromStart'] = output['chromStart'].astype(int)
    output['chromEnd'] = output['chromEnd'].astype(int)

    problemsTxn = db.getTxn(parent=txn)

    db.Problems(genome).put(output, txn=problemsTxn)

    problemsTxn.commit()

    output.to_csv(outputFile, sep='\t', index=False, header=False)

    return outputFile


def createNanProblems(args):
    data = {'chrom': args['chrom'], 'chromStart': [0], 'chromEnd': args['bases']}

    return pd.DataFrame(data)


def createProblems(group):
    chrom = group['chrom'].iloc[0]
    bases = group['bases'].iloc[0]
    chromStart = [0, ]
    gapEnd = group['gapEnd'].tolist()
    chromEnd = group['gapStart'].tolist()
    chromStart.extend(gapEnd)
    chromEnd.append(bases)

    if len(chromStart) != len(chromStart):
        return

    data = {'chrom': chrom, 'chromStart': chromStart, 'chromEnd': chromEnd}

    df = pd.DataFrame(data)
    return df[df['chromStart'] < df['chromEnd']]


def downloadAndUnpackFile(url, path):
    if not os.path.exists(path):
        with tempfile.NamedTemporaryFile(suffix='.txt.gz') as temp:
            # Gets FASTA file for genome
            with requests.get(url, allow_redirects=True, verify=False) as r:
                temp.write(r.content)
                temp.flush()
                temp.seek(0)
            with gzip.GzipFile(fileobj=temp, mode='r') as gz:
                # uncompress the flatfile
                with open(path, 'w+b') as faFile:
                    # Save to file
                    faFile.write(gz.read())
    return path


@retry
@txnAbortOnError
def getHubInfo(data, txn=None):
    print(data['user'], data['hub'])
    return db.HubInfo(data['user'], data['hub']).get(txn=txn)



