import scipy
import numpy as np
import pandas as pd
from glmnet_python import cvglmnet
from simpleBDB import retry, txnAbortOnError
from core.util import PLConfig as cfg, PLdb as db
import logging

log = logging.getLogger(__name__)


@retry
@txnAbortOnError
def runPrediction(data, txn=None):
    log.info('runPrediction')
    datapoints = getDataPoints(txn=txn)
    if datapoints is None:
        return

    learn(*datapoints, txn=txn)


def getDataPoints(txn=None):
    dataPoints = pd.DataFrame()

    cursor = db.ModelSummaries.getCursor(txn=None, bulk=True)

    current = cursor.next()

    while current is not None:
        key, modelSum = current
        if modelSum.empty:
            current = cursor.next()
            continue

        if modelSum['regions'].max() < 1:
            current = cursor.next()
            continue

        withPeaks = modelSum[modelSum['numPeaks'] > 0]

        noError = withPeaks[withPeaks['errors'] < 1]

        logPenalties = np.log10(noError['penalty'].astype(float))

        featuresDb = db.Features(*key)
        features = featuresDb.get(txn=txn)

        for penalty in logPenalties:
            datapoint = features.copy()

            datapoint['logPenalty'] = penalty

            dataPoints = dataPoints.append(datapoint, ignore_index=True)

        current = cursor.next()

    cursor.close()

    # TODO: Save datapoints, update ones which have changed, not all of them every time

    if dataPoints.empty:
        return
    Y = dataPoints['logPenalty']
    X = dataPoints.drop('logPenalty', 1)

    return dropBadCols(X, txn=txn), Y


def makePrediction(data):
    model = db.Prediction('model').get()
    print(model)


def dropBadCols(df, txn=None):
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    noNegatives = df.replace(-np.Inf, np.nan)
    output = noNegatives.dropna(axis=1)

    # Take a note of what columns were dropped so that can be later used during prediction
    # This line just compares the two column indices and finds the differences
    badCols = list(set(df.columns) - set(output.columns))
    db.Prediction('badCols').put(badCols, txn=txn)
    return output


def learn(X, Y, txn=None):
    X = X.to_numpy(dtype=np.float64, copy=True)
    Y = Y.to_numpy(dtype=np.float64, copy=True)
    cvfit = cvglmnet(x=X, y=Y)
    db.Prediction('model').put(cvfit, txn=txn)



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
