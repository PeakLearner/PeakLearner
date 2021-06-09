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
