import pandas as pd
from core.util import PLdb as db
from simpleBDB import retry, txnAbortOnError

lossColumns = ['penalty',
               'segments',
               'peaks',
               'totalBases',
               'bedGraphLines',
               'meanPenalizedCost',
               'totalUnpenalizedCost',
               'numConstraints',
               'meanIntervals',
               'maxIntervals']


@retry
@txnAbortOnError
def putLoss(data, txn=None):
    penalty = data['penalty']
    lossInfo = data['lossInfo']
    user = lossInfo['user']
    hub = lossInfo['hub']
    track = lossInfo['track']
    problem = lossInfo['problem']

    lossData = pd.read_json(data['lossData'])
    lossData['meanLoss'] = lossData['meanPenalizedCost'] - lossData['peaks']*lossData['penalty']

    lossDb = db.Loss(user, hub, track, problem['chrom'], problem['chromStart'], penalty)

    lossDb.put(lossData, txn=txn)

    return True


@retry
@txnAbortOnError
def getLoss(data, txn=None):
    lossDb = db.Loss(data['user'], data['hub'],
                     data['track'], data['ref'],
                     data['start'], data['penalty'])

    return lossDb.get(txn=txn)


@retry
@txnAbortOnError
def getAllLosses(data, txn=None):
    output = []

    lossCursor = db.Loss.getCursor(txn=txn, bulk=True)

    current = lossCursor.next()

    while current is not None:
        key, loss = current

        user, hub, track, ref, start, penalty = key

        loss['user'] = user
        loss['hub'] = hub
        loss['track'] = track
        loss['ref'] = ref
        loss['start'] = start
        loss['penalty'] = float(penalty)

        output.append(loss)

        current = lossCursor.next()

    lossCursor.close()

    return pd.concat(output)
