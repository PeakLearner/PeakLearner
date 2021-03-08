import pandas as pd
from api.util import PLdb as db
from .Handler import TrackHandler

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


class LossHandler(TrackHandler):
    """Handles Label Commands"""
    key = 'loss'

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        return {'put': putLoss}


def putLoss(data):
    penalty = data['penalty']
    lossInfo = data['lossInfo']
    user = lossInfo['user']
    hub = lossInfo['hub']
    track = lossInfo['track']
    problem = lossInfo['problem']

    lossData = pd.read_json(data['lossData'])
    lossData['meanLoss'] = lossData['meanPenalizedCost'] - lossData['peaks']*lossData['penalty']

    txn = db.getTxn()
    lossDb = db.Loss(user, hub, track, problem['chrom'], problem['chromStart'], penalty)

    lossDb.put(lossData, txn=txn)

    txn.commit()

    return True
