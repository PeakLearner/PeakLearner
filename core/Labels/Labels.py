import time

import numpy as np
import pandas as pd
from requests import Session

from core.Models import Models
from fastapi import Response
from core import models

labelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
jbrowseLabelColumns = ['ref', 'start', 'end', 'label']
jbrowseContigLabelColumns = ['ref', 'start', 'end', 'label', 'contigStart', 'contigEnd']


def addLabel(data, txn=None):
    # Duplicated because calls from updateLabel are causing freezing
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
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
    else:
        return Response(status_code=401)
    return data


def addHubLabels(data, txn=None):
    # Duplicated because calls from updateLabel are causing freezing
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
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
    else:
        return Response(status_code=401)
    return data


def deleteLabel(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
    if perms.hasPermission(data['authUser'], 'Label'):
        toRemove = pd.Series({'chrom': data['ref'],
                              'chromStart': data['start'],
                              'chromEnd': data['end']})

        labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
        removed, after = labels.remove(toRemove, txn=txn)
        db.Prediction('changes').increment(txn=txn)
        Models.updateAllModelLabels(data, after, txn)
        return True
    else:
        return Response(status_code=401)


def deleteHubLabels(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
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

    else:
        return Response(status_code=401)


def updateLabel(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
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
    else:
        return Response(status_code=401)


def updateHubLabels(data, txn=None):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)
    if perms is None:
        return Response(status_code=404)
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
    else:
        return Response(status_code=401)


def getLabels(db, data):
    perms = db.Permission(data['user'], data['hub']).get(txn=txn)

    if perms is None:
        return Response(status_code=404)

    if perms.hasPermission(data['authUser'], 'Label'):
        labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
        labelsDf = labels.getInBounds(data['ref'], data['start'], data['end'], txn=txn)
        if len(labelsDf.index) < 1:
            return []

        if data['contig']:
            labelsOut = labelsDf[labelColumns]
            hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
            contigs = db.Problems(hubInfo['genome']).get(txn=txn)
            labelsOut = labelsOut.apply(addContigToLabel, axis=1, args=(contigs,))
            labelsOut.columns = jbrowseContigLabelColumns
        else:
            labelsOut = labelsDf[labelColumns]
            labelsOut.columns = jbrowseLabelColumns
        try:
            labelsOut['lastModifiedBy'] = labelsDf['lastModifiedBy']
            labelsOut['lastModified'] = labelsDf['lastModifiedBy']
        except KeyError:
            pass

        # https://stackoverflow.com/a/14163209/14396857
        labelsOut = labelsOut.where(pd.notnull(labelsOut), None)

        return labelsOut
    else:
        return Response(status_code=401)


def getHubLabels(data, txn=None):
    output = []

    perms = db.Permission(data['user'], data['hub']).get(txn=txn)

    if perms is None:
        return Response(status_code=404)

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

            output.append(labels)
    else:
        return Response(status_code=401)

    output = pd.concat(output)

    if data['contig']:
        hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)
        contigs = db.Problems(hubInfo['genome']).get(txn=txn)
        output = output.apply(addContigToLabel, axis=1, args=(contigs,))
    return output


def addContigToLabel(row, contig):
    inBounds = contig.apply(db.checkInBounds, axis=1, args=(row['chrom'], row['chromStart'], row['chromEnd']))

    contigInBounds = contig[inBounds]

    if len(contigInBounds.index) == 1:
        contigRow = contigInBounds.iloc[0]
        row['contigStart'] = contigRow['chromStart']
        row['contigEnd'] = contigRow['chromEnd']

    return row


def hubInfoLabels(db: Session, hub):
    """Provides table with user as index row, and chrom as column name. Value is label counts across tracks for that user/chrom"""
    tracks = hub.join(models.Hub.tracks)
    print(tracks)
    labels = []
    for track in tracks:
        chroms = track.chroms.all()

        for chrom in chroms:
            print(chrom)
            raise Exception
        labelsDf = db.Labels(*key).get(txn=txn)
        labels.append(labelsDf)

    allLabels = pd.concat(labels)
    grouped = allLabels.groupby('chrom')
    chromLabelUserTotals = grouped.apply(checkUserTotal)

    labelTable = pd.DataFrame(chromLabelUserTotals.apply(pd.Series)).T.fillna(0).astype(np.int64).to_html().replace(' border="1"', '')

    return {'labelTable': labelTable.replace('dataframe', 'table'), 'numLabels': len(allLabels.index)}


def checkUserTotal(row):
    """Calculates the total number of labels for each unique user given a chrom"""
    unique = row['lastModifiedBy'].unique()

    out = {}

    for uniqueUser in unique:
        # This should be NaN
        if isinstance(uniqueUser, float):
            uniqueUser = 'Public'
            labelsByUser = row['lastModifiedBy'].isnull()
        else:
            labelsByUser = row['lastModifiedBy'] == uniqueUser

        total = labelsByUser.value_counts()

        try:
            numLabels = total[True]
        except KeyError:
            continue

        if uniqueUser is None:
            uniqueUser = 'Public'

        try:
            out[uniqueUser] += numLabels
        except KeyError:
            out[uniqueUser] = numLabels

    return out


def labelsStats(data, txn=None):
    chroms = labels = 0

    for key in db.Labels.db_key_tuples():
        labelsDf = db.Labels(*key).get(txn=txn)

        if labelsDf.empty:
            continue

        chroms = chroms + 1

        labels = labels + len(labelsDf.index)

    return chroms, labels
