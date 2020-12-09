import os
import json
import pandas as pd
from api.util import PLConfig as cfg, PLdb as db
from api.Handlers import HubHandler, ModelHandler as mh

labelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
jbrowseLabelColumns = ['ref', 'start', 'end', 'label']
problemColumns = ['chrom', 'chromStart', 'chromEnd']


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

    labelsDf = labelsDf[labelColumns]
    labelsDf.columns = jbrowseLabelColumns

    return labelsDf.to_dict('records')


def getProblems(data):
    if 'genome' not in data:
        data['genome'] = getGenome(data)

    problems = db.Problems(data['genome'])

    problemsInBounds = problems.getInBounds(data['ref'], data['start'], data['end'])

    if problemsInBounds is None:
        problemsPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'genomes', data['genome'], 'problems.bed')

        if not os.path.exists(problemsPath):
            location = HubHandler.generateProblems(data['genome'], problemsPath)
            if not location == problemsPath:
                raise Exception

        problemsDf = pd.read_csv(problemsPath, sep='\t', header=None)
        problems.put(problemsDf)

        problemsInBounds = problemsDf.apply(db.checkInBounds, axis=1, args=(data['ref'], data['start'], data['end']))

        return problemsInBounds.to_dict('records')

    return problemsInBounds.to_dict('records')




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
