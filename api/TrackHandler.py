import os
import json
import pandas as pd
from api import HubParse as hubParse, UCSCtoPeakLearner as UCSCtoPeakLearner
from api import PLConfig as cfg, JobHandler as jh, ModelHandler as mh, PLdb as db


jbrowseLabelColumns = ['ref', 'start', 'end', 'label']


def jsonInput(data):
    command = data['command']
    # for some reason data['args'] is a list containing a dict
    args = data['args']

    commandOutput = commands(command)(args)

    return commandOutput


def commands(command):
    command_list = {
        'addLabel': addLabel,
        'removeLabel': removeLabel,
        'updateLabel': updateLabel,
        'getLabels': getLabels,
        'parseHub': parseHub,
        'getProblems': getProblems,
        'getGenome': getGenome,
        'getTrackUrl': getTrackUrl,
        'getJob': jh.getJob,
        'updateJob': jh.updateJob,
        'removeJob': jh.removeJob,
        'getAllJobs': jh.getAllJobs,
        'getModel': mh.getModel,
        'getModelSummary': mh.getModelSummary,
        'putModel': mh.putModel,
    }

    return command_list.get(command, None)


def addLabel(data):
    # TODO: add user
    data['hub'], data['track'] = data['name'].split('/')

    label = 'unknown'

    # Duplicated because calls from updateLabel are causing freezing
    newLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})

    # TODO: Replace 1 with hub user NOT current user
    labels = db.Labels(1, data['hub'], data['track'], data['ref'])

    labels.add(newLabel)

    return data


# Removes label from label file
def removeLabel(data):
    # TODO: Add user
    data['hub'], data['track'] = data['name'].split('/')

    toRemove = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end']})

    labels = db.Labels(1, data['hub'], data['track'], data['ref'])
    labels.remove(toRemove)

    mh.updateAllModelLabels(data)

    return data


def updateLabel(data):
    # TODO: add user
    data['hub'], data['track'] = data['name'].split('/')

    label = data['label']

    updateLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})

    # TODO: Replace 1 with hub user NOT current user
    labels = db.Labels(1, data['hub'], data['track'], data['ref'])

    labels.add(updateLabel)

    mh.updateAllModelLabels(data)

    return data


def getLabels(data):
    # TODO: Add user
    data['hub'], data['track'] = data['name'].split('/')

    labels = getLabelsDf(data)

    if labels is None:
        return {}

    labels = labels[['chrom', 'chromStart', 'chromEnd', 'annotation']]
    labels.columns = jbrowseLabelColumns

    test = labels.to_dict('records')

    return test


def getLabelsDf(data):
    # TODO: Add user
    labels = db.Labels(1, data['hub'], data['track'], data['ref'])
    labelsDf = labels.get()
    if len(labelsDf.index) < 1:
        return
    labelsDf['inBounds'] = labelsDf.apply(mh.checkInBounds, axis=1, args=(data,))
    return labelsDf[labelsDf['inBounds']].drop(columns='inBounds')


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
    hub, track = data['name'].rsplit('/')

    trackListPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, hub, 'trackList.json')

    with open(trackListPath, 'r') as f:
        trackList = json.load(f)

        genomePath = trackList['include'][0].split('/')

        genome = genomePath[-2]

        return genome


def getTrackUrl(data):
    hub, track = data['name'].split('/')

    trackListPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, hub, 'trackList.json')

    with open(trackListPath) as f:
        trackList = json.load(f)
        for track in trackList['tracks']:
            if track['label'] == data['name']:
                out = track['urlTemplates'][0]['url']
                return out
    return
