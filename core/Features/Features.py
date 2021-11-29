import pandas as pd
from core.util import PLdb as db
from core.Prediction import Prediction
from simpleBDB import retry, txnAbortOnError
from .Models import FeatureData
from core import dbutil, models


def putFeatures(db, user, hub, track, featureData: FeatureData):
    """Saves features to be later used for prediction and learning"""
    problem = featureData.problem
    user, hub, track, chrom, contig, problem = dbutil.getContig(db,
                                                                user,
                                                                hub,
                                                                track,
                                                                problem['chrom'],
                                                                problem['start'],
                                                                make=True)
    featuresDf = pd.read_json(featureData.data)

    if len(featuresDf.index) != 1:
        raise ValueError

    contig.features = featuresDf.iloc[0]
    db.commit()
    db.refresh(contig)

    return True


@retry
@txnAbortOnError
def getFeatures(data, txn=None):
    """Retrieve a singular feature from the db"""
    features = db.Features(data['user'], data['hub'], data['track'], data['ref'], data['start']).get(txn=txn)

    if isinstance(features, dict):
        return
    elif isinstance(features, str):
        return

    return Prediction.dropBadCols(features, txn=txn)


