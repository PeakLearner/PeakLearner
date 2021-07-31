import time

import pandas as pd
from core.util import PLdb as db
from core.Models import Models
from simpleBDB import retry, txnAbortOnError

labelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
jbrowseLabelColumns = ['ref', 'start', 'end', 'label']


@retry
@txnAbortOnError
def addLabel(data, txn=None):
    # Duplicated because calls from updateLabel are causing freezing
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        newLabel = pd.Series({'chrom': data['ref'],
                              'chromStart': data['start'],
                              'chromEnd': data['end'],
                              'annotation': data['label'],
                              'createdBy': data['authUser'],
                              'lastModifiedBy': data['authUser'],
                              'lastModified': time.time()})
        labelsDb = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
        labels = labelsDb.get(txn=txn, write=True)

        if not labels.empty:
            inBounds = labels.apply(db.checkInBounds, axis=1, args=(data['ref'], data['start'], data['end']))
            # If there are any labels currently stored within the region which the new label is being added
            if inBounds.any():
                raise db.AbortTXNException

        labels = labels.append(newLabel, ignore_index=True).sort_values('chromStart', ignore_index=True)

        labelsDb.put(labels, txn=txn)
        db.Prediction('changes').increment(txn=txn)
        Models.updateAllModelLabels(data, labels, txn)
    return data


@retry
@txnAbortOnError
def addHubLabels(data, txn=None):
    # Duplicated because calls from updateLabel are causing freezing
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        newLabel = pd.Series({'chrom': data['ref'],
                              'chromStart': data['start'],
                              'chromEnd': data['end'],
                              'annotation': data['label'],
                              'createdBy': data['authUser'],
                              'lastModifiedBy': data['authUser'],
                              'lastModified': time.time()})

        if 'tracks' in data and data['tracks'] is not None:
            tracks = data['tracks']
        else:
            hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
            tracks = list(hubInfo['tracks'].keys())

        for track in tracks:
            data['track'] = track
            trackTxn = db.getTxn(parent=txn)
            labelsDb = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
            labels = labelsDb.get(txn=trackTxn, write=True)
            if not labels.empty:
                inBounds = labels.apply(db.checkInBounds, axis=1, args=(data['ref'], data['start'], data['end']))
                # If there are any labels currently stored within the region which the new label is being added
                if inBounds.any():
                    trackTxn.abort()
                    raise db.AbortTXNException

            labels = labels.append(newLabel, ignore_index=True).sort_values('chromStart', ignore_index=True)

            labelsDb.put(labels, txn=trackTxn)
            db.Prediction('changes').increment(txn=trackTxn)
            Models.updateAllModelLabels(data, labels, trackTxn)
            trackTxn.commit()
    return data


@retry
@txnAbortOnError
def deleteLabel(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        toRemove = pd.Series({'chrom': data['ref'],
                              'chromStart': data['start'],
                              'chromEnd': data['end']})

        labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
        removed, after = labels.remove(toRemove, txn=txn)
        db.Prediction('changes').increment(txn=txn)
        Models.updateAllModelLabels(data, after, txn)
        return True
    return False


@retry
@txnAbortOnError
def deleteHubLabels(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        labelToRemove = pd.Series({'chrom': data['ref'],
                                   'chromStart': data['start'],
                                   'chromEnd': data['end']})

        user = data['user']
        hub = data['hub']

        if 'tracks' in data and data['tracks'] is not None:
            tracks = data['tracks']
        else:
            hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
            tracks = list(hubInfo['tracks'].keys())

        for track in tracks:
            data['track'] = track
            trackTxn = db.getTxn(parent=txn)
            labelDb = db.Labels(user, hub, track, data['ref'])
            item, labels = labelDb.remove(labelToRemove, txn=trackTxn)
            db.Prediction('changes').increment(txn=trackTxn)
            Models.updateAllModelLabels(data, labels, trackTxn)
            trackTxn.commit()


@retry
@txnAbortOnError
def updateLabel(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        label = data['label']

        labelToUpdate = pd.Series({'chrom': data['ref'],
                                   'chromStart': data['start'],
                                   'chromEnd': data['end'],
                                   'annotation': label,
                                   'lastModifiedBy': data['authUser'],
                                   'lastModified': time.time()})
        labelDb = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
        db.Prediction('changes').increment(txn=txn)
        item, labels = labelDb.add(labelToUpdate, txn=txn)
        Models.updateAllModelLabels(data, labels, txn)


@retry
@txnAbortOnError
def updateHubLabels(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms.hasPermission(data['authUser'], 'Label'):
        labelToUpdate = pd.Series({'chrom': data['ref'],
                                   'chromStart': data['start'],
                                   'chromEnd': data['end'],
                                   'annotation': data['label'],
                                   'lastModifiedBy': data['authUser'],
                                   'lastModified': time.time()})

        user = data['user']
        hub = data['hub']

        if 'tracks' in data and data['tracks'] is not None:
            tracks = data['tracks']
        else:
            hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
            tracks = list(hubInfo['tracks'].keys())

        for track in tracks:
            data['track'] = track
            trackTxn = db.getTxn(parent=txn)
            labelDb = db.Labels(user, hub, track, data['ref'])
            db.Prediction('changes').increment(txn=trackTxn)
            item, labels = labelDb.add(labelToUpdate, txn=trackTxn)
            Models.updateAllModelLabels(data, labels, trackTxn)
            trackTxn.commit()

        return item.to_dict()


@retry
@txnAbortOnError
def getLabels(data, txn=None):
    labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    labelsDf = labels.getInBounds(data['ref'], data['start'], data['end'], txn=txn)
    if len(labelsDf.index) < 1:
        return []

    labelsDf = labelsDf[labelColumns]
    labelsDf.columns = jbrowseLabelColumns

    return labelsDf


@retry
@txnAbortOnError
def getHubLabels(data, txn=None):
    output = pd.DataFrame()

    perms = db.Permission(data['user'], data['hub']).get(txn=txn)

    if perms.hasPermission(data['authUser'], 'Label'):
        if 'tracks' in data and data['tracks'] is not None:
            tracks = data['tracks']
        else:
            hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
            tracks = list(hubInfo['tracks'].keys())

        for track in tracks:
            if 'ref' in data:
                labelsDb = db.Labels(data['user'], data['hub'], track, data['ref'])
                if 'start' in data and 'end' in data:
                    labels = labelsDb.getInBounds(data['ref'], data['start'], data['end'], txn=txn)
                else:
                    labels = labelsDb.get(txn=txn)
            else:
                availableRefs = db.Labels.keysWhichMatch(data['user'], data['hub'], track)

                labels = pd.DataFrame()

                for refKey in availableRefs:
                    labels = labels.append(db.Labels(*refKey).get(txn=txn))

            labels['track'] = track

            output = output.append(labels)
    return output


@retry
@txnAbortOnError
def hubInfoLabels(query, txn=None):
    labelKeys = db.Labels.keysWhichMatch(query['user'], query['hub'])

    numLabels = 0
    labels = {}
    for key in labelKeys:
        user, hub, track, chrom = key
        labelsDf = db.Labels(*key).get(txn=txn)
        numLabels += len(labelsDf.index)
        if track not in labels:
            labels[track] = {}

        labels[track][chrom] = labelsDf.to_html()

    return {'numLabels': numLabels, 'labels': labels}


@retry
@txnAbortOnError
def labelsStats(data, txn=None):
    chroms = labels = 0

    for key in db.Labels.db_key_tuples():
        labelsDf = db.Labels(*key).get(txn=txn)

        if labelsDf.empty:
            continue

        chroms = chroms + 1

        labels = labels + len(labelsDf.index)

    return chroms, labels
