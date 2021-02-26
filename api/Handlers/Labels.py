import pandas as pd
from api.util import PLdb as db
from api.Handlers import Models, Handler

labelColumns = ['chrom', 'chromStart', 'chromEnd', 'annotation']
jbrowseLabelColumns = ['ref', 'start', 'end', 'label']


class LabelHandler(Handler.TrackHandler):
    """Handles Label Commands"""
    key = 'labels'

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        return {'add': addLabel,
                'remove': removeLabel,
                'update': updateLabel,
                'get': getLabels}


def addLabel(data):
    label = 'unknown'

    # Duplicated because calls from updateLabel are causing freezing
    newLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})

    txn = db.getTxn()
    item, labels = db.Labels(data['user'], data['hub'], data['track'], data['ref']).add(newLabel, txn=txn)
    db.Prediction('changes').increment(txn=txn)
    Models.updateAllModelLabels(data, labels)
    txn.commit()
    return data


# Removes label from label file
def removeLabel(data):
    toRemove = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end']})

    txn = db.getTxn()
    labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    removed, after = labels.remove(toRemove, txn=txn)
    db.Prediction('changes').increment(txn=txn)
    Models.updateAllModelLabels(data, after)
    txn.commit()
    return removed.to_dict()


def updateLabel(data):
    label = data['label']

    updateLabel = pd.Series({'chrom': data['ref'],
                          'chromStart': data['start'],
                          'chromEnd': data['end'],
                          'annotation': label})
    txn = db.getTxn()
    labelDb = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    item, labels = labelDb.add(updateLabel, txn=txn)
    db.Prediction('changes').increment(txn=txn)
    Models.updateAllModelLabels(data, labels)
    txn.commit()
    return item.to_dict()


def getLabels(data):
    labels = db.Labels(data['user'], data['hub'], data['track'], data['ref'])
    labelsDf = labels.getInBounds(data['ref'], data['start'], data['end'])
    if len(labelsDf.index) < 1:
        return []

    labelsDf = labelsDf[labelColumns]
    labelsDf.columns = jbrowseLabelColumns

    return labelsDf.to_dict('records')


def stats():
    chroms = labels = 0

    for key in db.Labels.db_key_tuples():
        labelsDf = db.Labels(*key).get()

        if labelsDf.empty:
            continue

        chroms = chroms + 1

        labels = labels + len(labelsDf.index)

    return chroms, labels
