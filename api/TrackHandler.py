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
        'putModel': mh.putModel,
    }

    return command_list.get(command, None)


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

    update = True

    if 'label' not in data.keys():
        update = False
        label = 'unknown'
    else:
        label = data['label']

    newLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})

    # TODO: Replace 1 with hub user NOT current user
    labels = db.Labels(1, data['hub'], data['track'], data['ref'])

    labels.add(newLabel)

    if update:
        mh.updateAllModelLabels(data)

    return data


def getLabels(data):
    # TODO: Add user
    data['hub'], data['track'] = data['name'].split('/')

    print('before getting Labels')

    labels = getLabelsDf(data)

    print('getLabels', labels)

    if len(labels.index) < 1:
        return {}

    print('getLabels after if')

    labels.columns = jbrowseLabelColumns

    print('labels', labels)

    test = labels.to_dict('records')

    print('test', test)

    return test


def getLabelsDf(data):
    # TODO: Add user
    print('beforeCreationLabels')
    labels = db.Labels(1, data['hub'], data['track'], data['ref'])
    print('afterCreationLabels')
    labelsDf = labels.get()
    print('getLabelsDf', labelsDf)
    return labelsDf.apply(mh.checkInBounds, axis=1, args=(data,))


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


def getHubInfo(data):
    hub, track = data.rsplit('/')

    genome = getGenome(data)

    genomePath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'genomes/', genome)

    trackListPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, hub, 'trackList.json')

    output = {'hub': hub, 'genomePath': genomePath, 'tracks': []}

    with open(trackListPath, 'r') as f:
        trackList = json.load(f)

        for track in trackList['tracks']:
            trackLabel = track['label']
            url = track['urlTemplates'][0]['url']

            output['tracks'].append({'name': trackLabel, 'coverage': url})

        return output


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
