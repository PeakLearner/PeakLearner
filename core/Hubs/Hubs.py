import datetime
import os
import json
import gzip

import numpy as np
import requests
import tempfile
import threading
import pandas as pd
from sqlalchemy.orm import Session

from core import models, dbutil
from core.Jobs import Jobs
from fastapi import Response
from core.Labels import Labels
from core.Models import Models
from core.Handlers import Tracks
from core.Permissions import Permissions
from core.util import PLConfig as cfg, bigWigUtil


def getHubJsons(db, owner, hub, handler):
    """Return the hub info in a way which JBrowse can understand"""
    if handler == 'trackList.json':

        hubInfo = getHubInfo(db, owner, hub)

        return createTrackListWithHubInfo(hubInfo, owner, hub)
    else:
        print('no handler for %s' % handler)


def goToRegion(db: Session, user, hub, navigateTo):
    user, hub = dbutil.getHub(db, user, hub)
    problems = hub.getProblems(db)

    trackProblems = []
    for track in hub.tracks.all():
        grouped = problems.groupby(['chrom'], as_index=False)
        problemLabels = grouped.apply(checkProblemForLabels, db, track)
        problemLabels['track'] = track.name
        trackProblems.append(problemLabels)

    trackProblems = pd.concat(trackProblems)

    problemGroups = trackProblems.groupby(['chrom', 'start', 'end'], as_index=False)

    toCheck = navigateTo.lower() == 'labeled'

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


def checkProblemForLabels(chromGroup, db, track):
    chrom = track.chroms.filter(models.Chrom.name == chromGroup.name).first()

    if chrom is None:
        chromGroup['labeled'] = False
        return chromGroup

    labels = chrom.getLabels(db)

    chromGroup['labeled'] = chromGroup.apply(checkLabelsInBoundsOnChrom, axis=1, args=(labels,))

    return chromGroup


def checkLabelsInBoundsOnChrom(row, labels):
    inBounds = labels.apply(bigWigUtil.checkInBounds, axis=1, args=(row['start'], row['end']))
    return inBounds.any()


def removeUserFromHub(request, owner, hubName, delUser, txn=None):
    """Removes a user from a hub given the hub name, owner userid, and the userid of the user to be removed
    Adjusts the db.HubInfo object by calling the remove() function on the removed userid from the ['users'] item of the
    db.HubInfo object.
    """

    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    txn = db.getTxn(parent=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn, write=True)

    if perms is None:
        return Response(status_code=404)

    if not perms.hasPermission(authUser, 'Hub'):
        return Response(status_code=401)

    del perms.users[delUser]

    permDb.put(perms, txn=txn)
    txn.commit()


def addTrack(owner, hubName, userid, category, trackName, url, txn=None):
    hub = db.HubInfo(owner, hubName).get(txn=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn)

    if perms is None:
        return Response(status_code=404)

    if perms.hasPermission(userid, 'Hub'):
        hub['tracks'][trackName] = {'categories': category, 'key': trackName, 'url': url}
        db.HubInfo(owner, hubName).put(hub, txn=txn)
    else:
        return Response(status_code=401)


def removeTrack(owner, hubName, userid, trackName, txn=None):
    hub = db.HubInfo(owner, hubName).get(txn=txn)

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn)

    if perms is None:
        return Response(status_code=404)

    if not perms.hasPermission(userid, 'Hub'):
        return Response(status_code=401)

    del hub['tracks'][trackName]
    db.HubInfo(owner, hubName).put(hub, txn=txn)


def deleteHub(owner, hub, userid, txn=None):
    if userid != owner:
        raise AbortTXNException

    hub_info = None
    db.HubInfo(userid, hub).put(hub_info, txn=txn)


def getHubInfosForMyHubs(db: Session, authUser):
    hubInfos = {}
    usersdict = {}
    permissions = {}

    for hub in db.query(models.Hub).all():

        owner = db.query(models.User).filter(models.User.id == hub.owner).first()
        hubName = hub.name

        hubInfo = getHubInfo(db, owner, hub)

        if not Permissions.hasViewPermission(hub, authUser):
            continue

        permissions[(owner, hubName)] = Permissions.getHubPermissions(db, hub)

        num_labels = 0

        hubInfo['numLabels'] = num_labels

        hubInfos[(owner, hubName)] = hubInfo

    return {"user": authUser.name,
            "hubInfos": hubInfos,
            "usersdict": usersdict,
            "permissions": permissions}


def makeHubPublic(data, txn=None):
    userid = data['currentUser']
    owner = data['user']
    hubName = data['hub']

    if userid != owner:
        perms = db.Permission(owner, hubName).get(txn=txn)
        if perms is None:
            return Response(status_code=404)

        if not perms.hasPermission(userid, 'Hub'):
            return Response(status_code=401)

    hub = db.HubInfo(owner, hubName).get(txn=txn, write=True)
    hub['isPublic'] = data['chkpublic']
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


def parseHub(db: Session, data, user):
    parsed = parseUCSC(data, user)
    # Add a way to configure hub here somehow instead of just loading everything
    return createHubFromParse(db, parsed)


# All this should probably be done asynchronously
def createHubFromParse(db: Session, parsed):
    # Will need to add a way to add additional folder depth for userID once authentication is added
    owner = db.query(models.User).filter(models.User.name == parsed['user']).first()
    if owner is None:
        owner = models.User(name=parsed['user'])
        db.add(owner)
        db.commit()
        db.refresh(owner)

    genomesFile = parsed['genomesFile']

    # This will need to be updated if there are multiple genomes in file
    genome = db.query(models.Genome).filter(models.Genome.name == genomesFile['genome']).first()
    if genome is None:
        genome = models.Genome(name=genomesFile['genome'])
        db.add(genome)
        db.commit()
        db.refresh(genome)

    hub = owner.hubs.filter(models.Hub.name == parsed['hub']).first()

    if hub is None:
        hub = models.Hub(owner=owner.id, name=parsed['hub'], genome=genome.id, public=parsed['isPublic'])
        db.add(hub)
        db.flush()
        db.refresh(hub)

    dataPath = cfg.dataPath

    includes = getGeneTracks(genome, dataPath)

    # Generate problems for this genome

    problems = generateProblems(db, genome, dataPath)

    problemPath = generateProblemTrack(problems)

    includes.append(problemPath)

    getRefSeq(genome, dataPath, includes)

    path = storeHubInfo(db, owner, hub, genomesFile['trackDb'])

    return path


def storeHubInfo(db: Session, owner, hub, tracks):
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

            trackInDb = hub.tracks.filter(models.Track.name == track['shortLabel']).first()
            if trackInDb is None:
                trackInDb = models.Track(
                    hub=hub.id,
                    categories=categories,
                    name=track['shortLabel'],
                    url=coverage['bigDataUrl'])

                db.add(trackInDb)
                db.flush()
                db.refresh(trackInDb)

            checkForPrexistingLabels(db, coverage['bigDataUrl'], hub, trackInDb)

    return '/%s/' % os.path.join(owner.name, hub.name)


def checkForPrexistingLabels(db: Session, coverageUrl, hub, track):
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
            labels.columns = ['chrom', 'start', 'end', 'annotation']

    grouped = labels.groupby(['chrom'], as_index=False)

    for chromName, group in grouped:
        group = group.sort_values('start', ignore_index=True)

        chrom = track.chroms.filter(models.Chrom.name == chromName).first()

        if chrom is None:
            chrom = models.Chrom(track=track.id, name=chromName)
            db.add(chrom)
            db.flush()
            db.refresh(chrom)
            db.refresh(track)

        for _, row in group.iterrows():
            asDict = row.to_dict()

            if 'createdBy' in asDict:
                del asDict['createdBy']

            checkLabel = chrom.labels.filter(models.Label.start == asDict['start']).first()

            if checkLabel is None:
                if 'lastModifiedBy' in asDict:
                    lmb = asDict['lastModifiedBy']

                    if not isinstance(lmb, str):
                        asDict['lastModifiedBy'] = 'Public'

                    lastModifiedBy = db.query(models.User).filter(
                        models.User.name == asDict['lastModifiedBy']).first()
                else:
                    asDict['lastModifiedBy'] = 'Public'
                    lastModifiedBy = db.query(models.User).filter(
                        models.User.name == 'Public').first()

                if 'lastModified' in asDict:
                    lm = asDict['lastModified']
                    if lm is None or np.nan:
                        asDict['lastModified'] = datetime.datetime.now()
                else:
                    asDict['lastModified'] = datetime.datetime.now()

                if lastModifiedBy is None:
                    lastModifiedBy = models.User(name=asDict['lastModifiedBy'])
                    db.add(lastModifiedBy)
                    db.flush()
                    db.refresh(lastModifiedBy)

                label = models.Label(chrom=chrom.id,
                                     start=asDict['start'],
                                     end=asDict['end'],
                                     annotation=asDict['annotation'],
                                     lastModified=asDict['lastModified'],
                                     lastModifiedBy=lastModifiedBy.id)

                chrom.labels.append(label)
                db.commit()

        checkSubmitPregensForChrom(db, hub, chrom, group)

    return True


def checkSubmitPregensForChrom(db, hub, chrom, labels):
    problems = hub.getProblems(db, ref=chrom)

    for _, problem in problems.iterrows():
        inBounds = labels.apply(bigWigUtil.checkInBounds, axis=1, args=(problem['start'], problem['end']))

        contig = chrom.contigs.filter(models.Contig.problem == problem['id']).first()

        if contig is None:
            contig = models.Contig(chrom=chrom.id, problem=problem['id'])
            db.add(contig)
            db.flush()
            db.refresh(contig)

        if inBounds.any():
            return Jobs.submitPregenJob(db, contig)
        else:
            return Jobs.submitFeatureJob(db, contig)


def getRefSeq(genome, path, includes):
    genomeRelPath = os.path.join('genomes', genome.name)

    genomePath = os.path.join(path, genomeRelPath)

    includes = formatIncludes(includes, genomePath)

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            print(genomePath, "does not exist")
            return

    genomeUrl = cfg.geneUrl + genome.name + '/bigZips/' + genome.name + '.fa.gz'
    genomeFaPath = os.path.join(genomePath, genome.name + '.fa')
    genomeFaiPath = genomeFaPath + '.fai'

    downloadRefSeq(genomeUrl, genomeFaPath, genomeFaiPath)

    genomeConfigPath = os.path.join(genomePath, 'trackList.json')

    with open(genomeConfigPath, 'w') as genomeCfg:
        genomeFile = genome.name + '.fa.fai'
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
    genomePath = os.path.join(dataPath, 'genomes', genome.name)

    genesPath = os.path.join(genomePath, 'genes')

    if not os.path.exists(genesPath):
        try:
            os.makedirs(genesPath)
        except OSError:
            return

    genesUrl = "%s%s/database/" % (cfg.geneUrl, genome.name)

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


def parseUCSC(data, user):
    url = data.url
    hubReq = requests.get(url, allow_redirects=True, verify=False)
    if not hubReq.status_code == 200:
        return None
    path = ""
    if url.find('/'):
        vals = url.rsplit('/', 1)
        path = vals[0]

    lines = hubReq.text.split('\n')

    hub = readUCSCLines(lines)

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


def generateProblems(db: Session, genome, path):
    genesUrl = "%s%s/database/" % (cfg.geneUrl, genome.name)
    genomePath = os.path.join(path, 'genomes', genome.name)
    outputFile = os.path.join(genomePath, 'problems.bed')


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

    def putProblems(row):
        problem = genome.problems.filter(models.Problem.chrom == row['chrom']) \
            .filter(models.Problem.start == row['chromStart']).first()
        if problem is None:
            problem = models.Problem(genome=genome.id,
                                     chrom=row['chrom'],
                                     start=row['chromStart'],
                                     end=row['chromEnd'])
            db.add(problem)
            db.flush()
            db.refresh(problem)

    output.apply(putProblems, axis=1)

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


def getHubInfo(db, owner, hub):
    tracks = hub.tracks.all()

    genome = db.query(models.Genome).get(hub.genome)

    hubInfoToReturn = {'owner': owner.name,
                       'name': hub.name,
                       'genome': genome.name,
                       'public': hub.public,
                       'tracks': {}}

    for track in tracks:
        trackDict = {'categories': track.categories,
                     'key': track.name,
                     'url': track.url}
        hubInfoToReturn['tracks'][track.name] = trackDict

    return hubInfoToReturn
