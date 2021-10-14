import pandas as pd
from core.util import PLdb as db
from core.Prediction import Prediction
from simpleBDB import retry, txnAbortOnError


@retry
@txnAbortOnError
def putFeatures(data, txn=None):
    """Saves features to be later used for prediction and learning"""
    if not isinstance(data['data'], list) and not len(data['data']) == 1:
        raise Exception(data['data'])

    problem = data['problem']
    features = db.Features(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'])
    features.put(pd.Series(data['data'][0]), txn=txn)

    return True


@retry
@txnAbortOnError
def getFeatures(data, txn=None):
    """Retrieve a singular feature from the db"""
    features = db.Features(data['user'], data['hub'], data['track'], data['ref'], data['start']).get(txn=txn)

    if isinstance(features, dict):
        return

    return Prediction.dropBadCols(features, txn=txn)


