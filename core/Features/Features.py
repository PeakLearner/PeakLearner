import pandas as pd
from sqlalchemy.orm import Session
from core.Prediction import Prediction
from simpleBDB import retry, txnAbortOnError
from .Models import FeatureData
from core import dbutil, models


def putFeatures(db: Session, user, hub, track, featureData: FeatureData):
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
def getFeatures(db: Session, user, hub, track, ref, start):
    """Retrieve a singular feature from the db"""
    user, hub, track, chrom, contig = dbutil.getContig(db, user, hub, track, ref, start)
    if contig is None:
        return
    features = contig.features

    if features is None:
        return

    return Prediction.dropBadCols(features)
