import os
import json
import pandas as pd
from api import HubParse as hubParse, UCSCtoPeakLearner as UCSCtoPeakLearner
from api import PLConfig as cfg, PLdb as db
from api.Handlers import ModelHandler as mh

jbrowseLabelColumns = ['ref', 'start', 'end', 'label']


def addLabel(data):
    # TODO: add user
    data['user'] = 1
    data['hub'], data['track'] = data['name'].split('/')

    label = 'unknown'

    # Duplicated because calls from updateLabel are causing freezing
    newLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})

    txn = db.getTxn()
    db.Labels(data['user'], data['hub'], data['track'], data['ref']).add(newLabel, txn=txn)
    txn.commit()

    return data


# Removes label from label file
def removeLabel(data):
    # TODO: Add user
    data['user'] = 1
    data['hub'], data['track'] = data['name'].split('/')

    toRemove = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end']})

    txn = db.getTxn()
    labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    removed, after = labels.remove(toRemove, txn=txn)
    txn.commit()
    mh.updateAllModelLabels(data, after)
    return removed.to_dict()


def updateLabel(data):
    # TODO: add user
    data['user'] = 1
    data['hub'], data['track'] = data['name'].split('/')

    label = data['label']

    updateLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})
    txn = db.getTxn()
    labelDb = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    item, labels = labelDb.add(updateLabel, txn=txn)
    txn.commit()
    mh.updateAllModelLabels(data, labels)
    return item.to_dict()


def getLabels(data):
    # TODO: Add user
    data['user'] = 1
    data['hub'], data['track'] = data['name'].split('/')
    labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    labelsDf = labels.getInBounds(data['ref'], data['start'], data['end'])
    if len(labelsDf.index) < 1:
        return {}

    labelsDf = labelsDf[['chrom', 'chromStart', 'chromEnd', 'annotation']]
    labelsDf.columns = jbrowseLabelColumns

    return labelsDf.to_dict('records')


def parseHub(data):
    hub = hubParse.parse(data)
    # Add a way to configure hub here somehow instead of just loading everything
    return UCSCtoPeakLearner.convert(hub)


def getProblems(data):
    if 'genome' not in data:
        data['genome'] = getGenome(data)

    rel_path = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'genomes', data['genome'], 'problems.bed')
    refseq = data['ref']
    start = data['start']
    end = data['end']

    output = []

    if not os.path.exists(rel_path):
        return output

    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':
            lineVals = current_line.split()

            lineStart = int(lineVals[1])

            lineEnd = int(lineVals[2])

            if lineVals[0] == refseq:

                lineIfStartIn = (lineStart >= start) and (lineStart <= end)
                lineIfEndIn = (lineEnd >= start) and (lineEnd <= end)
                wrap = (lineStart < start) and (lineEnd > end)

                if lineIfStartIn or lineIfEndIn or wrap:
                    output.append({"ref": refseq, "start": lineStart,
                                   "end": lineEnd})

            current_line = f.readline()

    return output


def getGenome(data):
    data['hub'], data['track'] = data['name'].split('/')

    trackListPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, data['hub'], 'trackList.json')

    with open(trackListPath, 'r') as f:
        trackList = json.load(f)

        genomePath = trackList['include'][0].split('/')

        genome = genomePath[-2]

        return genome


def getTrackUrl(data):
    trackListPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, data['hub'], 'trackList.json')
    data['name'] = os.path.join(data['hub'], data['track'])

    with open(trackListPath) as f:
        trackList = json.load(f)
        for track in trackList['tracks']:
            if track['label'] == data['name']:
                out = track['urlTemplates'][0]['url']
                return out
    return
