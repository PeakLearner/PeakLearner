import pickle

import scipy
import numpy as np
import pandas as pd
from core import models, dbutil
from glmnet_python import cvglmnet
from sqlalchemy.orm import Session
from glmnet_python import cvglmnetPredict
from fastapi import Response
import logging

log = logging.getLogger(__name__)


def runPrediction(db: Session):
    log.info('runPrediction')
    datapoints = getDataPoints(db)
    if datapoints is None:
        return

    return learn(db, *datapoints)


def getDataPoints(db: Session):
    query = db.query(models.ModelSum).filter(models.ModelSum.errors < 1).filter(models.ModelSum.regions >= 1)
    modelSums = pd.read_sql(query.statement, db.bind).set_index('id')
    modelSums = modelSums.drop('loss', axis=1)

    logPenalties = np.log10(modelSums['penalty'].astype(float))

    def addFeatures(row):
        contig = db.query(models.Contig).get(row['contig'])
        return contig.features

    features = modelSums.apply(addFeatures, axis=1)

    noNegatives = features.replace(-np.Inf, np.nan)

    afterDrop = noNegatives.dropna(axis=1)

    badCols = list(set(features.columns) - set(afterDrop.columns))

    # Need to know which columns were dropped just in case it would drop too little columns for prediction
    badColsInDb = db.query(models.Other).filter(models.Other.name == 'badCols').first()

    if badColsInDb is None:
        badColsInDb = models.Other(name='badCols', data=badCols)
        db.add(badColsInDb)
        db.flush()
        db.refresh(badColsInDb)
    else:
        badColsInDb.data = badCols
        db.flush()
        db.refresh(badColsInDb)
    return afterDrop, logPenalties


def learn(db: Session, X, Y):
    if len(X.index) < 10:
        return Response(status_code=204)
    X = X.to_numpy(dtype=np.float64, copy=True)
    Y = Y.to_numpy(dtype=np.float64, copy=True)
    cvfit = cvglmnet(x=X, y=Y)

    model = db.query(models.Other).filter(models.Other.name == 'model').first()

    if model is None:
        model = models.Other(name='model', data=cvfit)
        db.add(model)
        db.flush()
        db.refresh(model)
    else:
        model.data = cvfit
        db.flush()
        db.refresh(model)


def getPenalty(db: Session, contig):
    features = contig.features

    if not isinstance(features, pd.Series):
        return False

    model = db.query(models.Other).filter(models.Other.name == 'prediction').first()

    if model is None:
        return False

    if not isinstance(model, dict):
        return False

    colsToDrop = db.query(models.Other).filter(models.Other.name == 'badCols').first()

    if colsToDrop is None:
        raise Exception

    featuresDropped = features.drop(labels=colsToDrop)

    prediction = predictWithFeatures(featuresDropped, model)

    if prediction is None:
        return False

    return float(10 ** prediction)


def predictWithFeatures(features, model):
    if not isinstance(features, pd.Series):
        raise Exception(features)

    featuresDf = pd.DataFrame().append(features, ignore_index=True)
    guess = cvglmnetPredict(model, newx=featuresDf, s='lambda_min')[0][0]

    if np.isnan(guess):
        return

    return guess



# Taken from the glmnet_python library, added a return to it so it can be saved
# Not too important for functionality, just info about the system
def cvglmnetPlotReturn(cvobject, sign_lambda=1.0, **options): # pragma: no cover
    import matplotlib.pyplot as plt

    sloglam = sign_lambda * scipy.log(cvobject['lambdau'])

    fig = plt.gcf()
    ax1 = plt.gca()
    # fig, ax1 = plt.subplots()

    plt.errorbar(sloglam, cvobject['cvm'], cvobject['cvsd'], ecolor=(0.5, 0.5, 0.5), **options
                 )
    # plt.hold(True)
    plt.plot(sloglam, cvobject['cvm'], linestyle='dashed',
             marker='o', markerfacecolor='r')

    xlim1 = ax1.get_xlim()
    ylim1 = ax1.get_ylim()

    xval = sign_lambda * scipy.log(scipy.array([cvobject['lambda_min'], cvobject['lambda_min']]))
    plt.plot(xval, ylim1, color='b', linestyle='dashed',
             linewidth=1)

    if cvobject['lambda_min'] != cvobject['lambda_1se']:
        xval = sign_lambda * scipy.log([cvobject['lambda_1se'], cvobject['lambda_1se']])
        plt.plot(xval, ylim1, color='b', linestyle='dashed',
                 linewidth=1)

    ax2 = ax1.twiny()
    ax2.xaxis.tick_top()

    atdf = ax1.get_xticks()
    indat = scipy.ones(atdf.shape, dtype=scipy.integer)
    if sloglam[-1] >= sloglam[1]:
        for j in range(len(sloglam) - 1, -1, -1):
            indat[atdf <= sloglam[j]] = j
    else:
        for j in range(len(sloglam)):
            indat[atdf <= sloglam[j]] = j

    prettydf = cvobject['nzero'][indat]

    ax2.set(XLim=xlim1, XTicks=atdf, XTickLabels=prettydf)
    ax2.grid()
    ax1.yaxis.grid()

    ax2.set_xlabel('Degrees of Freedom')

    #  plt.plot(xlim1, [ylim1[1], ylim1[1]], 'b')
    #  plt.plot([xlim1[1], xlim1[1]], ylim1, 'b')

    if sign_lambda < 0:
        ax1.set_xlabel('-log(Lambda)')
    else:
        ax1.set_xlabel('log(Lambda)')

    ax1.set_ylabel(cvobject['name'])

    return plt
