import datetime
import time

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from core.Models import Models
from fastapi import Response
from core import models
from core import dbutil
from core.util.bigWigUtil import checkInBounds

labelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
jbrowseLabelColumns = ['ref', 'start', 'end', 'label']
jbrowseContigLabelColumns = ['ref', 'start', 'end', 'label', 'contigStart', 'contigEnd']


def onlyInBoundsAsDf(toCheck, start=None, end=None):
    return pd.DataFrame(onlyInBounds(toCheck, start, end))


def onlyInBounds(toCheck, start=None, end=None):
    output = []

    for checking in toCheck:
        if start and not end:
            if checking['start'] >= start:
                output.append(checking)
        elif end and not start:
            if checking['end'] <= end:
                output.append(checking)
        elif start and end:
            if start <= checking['start'] <= end:
                output.append(checking)
            elif start <= checking['end'] <= end:
                output.append(checking)
            else:
                output.append(checking)

    return output


def getLabels(db, user, hub, track, ref: str = None, start: int = None,
              end: int = None, make=False):
    user, hub, track = dbutil.getTrack(db, user, hub, track)

    if ref:
        user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, ref, make=make)
        if chrom is None:
            return
        out = chrom.getLabels(db)
        return out
    else:
        out = track.getLabels(db)
        return out


def putLabel(db, authUser, user, hub, track, label):
    out = dbutil.getChromAndCheckPerm(db, authUser, user, hub, track, label.ref, 'Label', make=True)
    if isinstance(out, Response):
        return out

    user, hub, track, chrom = out

    labelsDf = chrom.getLabels(db)

    if not labelsDf.empty:
        inBounds = labelsDf.apply(checkInBounds, axis=1, args=(label.start, label.end))

        if inBounds.any():
            return Response(status_code=406)

    newLabel = models.Label(chrom=chrom.id,
                            annotation=label.label,
                            start=label.start,
                            end=label.end,
                            lastModified=datetime.datetime.now(),
                            lastModifiedBy=authUser.id)

    db.add(newLabel)
    db.flush()
    db.refresh(chrom)
    db.refresh(newLabel)

    labelAsSeries = pd.Series({'label_id': newLabel.id,
                               'chrom': label.ref,
                               'annotation': newLabel.annotation,
                               'start': newLabel.start,
                               'end': newLabel.end,
                               'lastModified': newLabel.lastModified,
                               'lastModifiedBy': newLabel.lastModifiedBy})

    labelsDf = labelsDf.append(labelAsSeries, ignore_index=True).sort_values('start', ignore_index=True)

    Models.updateAllModelLabels(db, authUser, user, hub, track, chrom, labelsDf, label)

    return newLabel


def updateLabel(db, authUser, user, hub, track, label):
    out = dbutil.getChromAndCheckPerm(db, authUser, user, hub, track, label.ref, 'Label')

    if isinstance(out, Response):
        return out

    user, hub, track, chrom = out

    if chrom is None:
        return Response(status_code=404)

    labelToUpdate = chrom.labels.filter(models.Label.start == label.start and models.Label.end == label.end).first()

    if labelToUpdate is None:
        return Response(status_code=404)
    else:
        labelToUpdate.lastModifiedBy = authUser.id
        labelToUpdate.lastModified = datetime.datetime.now()
        labelToUpdate.annotation = label.label

        chrom.labels.append(labelToUpdate)
        db.flush()
        db.refresh(chrom)
        db.refresh(labelToUpdate)

        return labelToUpdate


def deleteLabel(db, authUser, user, hub, track, label):
    out = dbutil.getChromAndCheckPerm(db, authUser, user, hub, track, label.ref, 'Label')

    if isinstance(out, Response):
        return out

    user, hub, track, chrom = out

    if chrom is None:
        return Response(status_code=404)

    labelToDelete = chrom.labels.filter(models.Label.start == label.start and models.Label.end == label.end).first()

    if labelToDelete is None:
        return Response(status_code=404)
    else:

        db.delete(labelToDelete)
        db.flush()
        db.refresh(chrom)

        return labelToDelete


def hubInfoLabels(db: Session, user, hub):
    """Provides table with user as index row, and chrom as column name. Value is label counts across tracks for that user/chrom"""

    user, hub = dbutil.getHub(db, user, hub)

    labels = hub.getAllLabels(db)

    allLabels = pd.concat(labels)
    grouped = allLabels.groupby('chrom')

    def checkUserTotal(row):
        """Calculates the total number of labels for each unique user given a chrom"""
        unique = row['lastModifiedBy'].unique()

        out = {}

        for uniqueUser in unique:
            labelsByUser = row['lastModifiedBy'] == uniqueUser

            total = labelsByUser.value_counts()

            try:
                numLabels = total[True]
            except KeyError:
                continue

            try:
                out[uniqueUser] += numLabels
            except KeyError:
                out[uniqueUser] = numLabels

        outWithUsernames = {}

        for key, value in out.items():
            db.flush()
            user = db.query(models.User).get(key)
            outWithUsernames[user.name] = value

        return outWithUsernames

    chromLabelUserTotals = grouped.apply(checkUserTotal)

    labelTable = pd.DataFrame(chromLabelUserTotals.apply(pd.Series)).T.fillna(0).astype(np.int64).to_html().replace(' border="1"', '')

    return {'labelTable': labelTable.replace('dataframe', 'table'), 'numLabels': len(allLabels.index)}


def labelsStats(db: Session):
    chroms = labels = 0

    for chrom in db.query(models.Chrom).all():
        labelsDf = chrom.getLabels(db)

        if labelsDf.empty:
            continue

        chroms = chroms + 1

        labels = labels + len(labelsDf.index)

    return chroms, labels
