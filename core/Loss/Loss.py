import pandas as pd
from core import models
from . import Models
from sqlalchemy.orm import Session

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


def getLoss(data, txn=None):
    lossDb = db.Loss(data['user'], data['hub'],
                     data['track'], data['ref'],
                     data['start'], data['penalty'])

    return lossDb.get(txn=txn)
