import pandas as pd
import numpy as np
import scipy

from glmnet_python import cvglmnet
from api.util import PLConfig as cfg, PLdb as db
import time

shutdownServer = False


def runLearning():
    lastRun = time.time()
    firstStart = True

    timeDiff = lambda: time.time() - lastRun

    try:
        while not shutdownServer:
            if timeDiff() > cfg.timeBetween or firstStart:
                print('starting prediction model generate')
                firstStart = False
                lastRun = time.time()
                # Compile and process the datapoints to learn with
                datapoints = getDataPoints()
                if datapoints is not None:
                    learn(*datapoints)
                    print('end learning')
                else:
                    print('nonDataPoints')
            else:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass


# Checks that there are enough changes and labeled regions to begin learning
def check():
    changes = db.Prediction('changes').get()
    if changes > cfg.numChanges:
        if not db.Prediction.has_key('EnoughLabels'):
            db.Prediction('EnoughLabels').put(False)

        if db.Prediction('EnoughLabels').get():
            return True
        else:
            if checkLabelRegions():
                db.Prediction('EnoughLabels').put(True)
                return True
            return False
    return False


def checkLabelRegions():
    labeledRegions = 0
    for key in db.ModelSummaries.db_key_tuples():
        modelSum = db.ModelSummaries(*key).get()
        if not modelSum.empty:
            if modelSum['regions'].max() > 0:
                labeledRegions = labeledRegions + 1

    return labeledRegions > cfg.minLabeledRegions


def getDataPoints():
    if not check():
        return

    dataPoints = pd.DataFrame()

    for key in db.ModelSummaries.db_key_tuples():
        modelSum = db.ModelSummaries(*key).get()
        if modelSum.empty:
            continue

        if modelSum['regions'].max() < 1:
            continue

        withPeaks = modelSum[modelSum['numPeaks'] > 0]

        noError = withPeaks[withPeaks['errors'] < 1]

        logPenalties = np.log10(noError['penalty'].astype(float))

        featuresDb = db.Features(*key)
        featuresTxn = db.getTxn()
        features = featuresDb.get(txn=featuresTxn, write=True)

        for penalty in logPenalties:
            datapoint = features.copy()

            datapoint['logPenalty'] = penalty

            dataPoints = dataPoints.append(datapoint, ignore_index=True)

        featuresTxn.commit()

    # TODO: Save datapoints, update ones which have changed, not all of them every time

    Y = dataPoints['logPenalty']
    X = dataPoints.drop('logPenalty', 1)

    return dropBadCols(X), Y


def makePrediction(data):
    model = db.Prediction('model').get()
    print(model)


def dropBadCols(df):
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    noNegatives = df.replace(-np.Inf, np.nan)
    output = noNegatives.dropna(axis=1)

    # Take a note of what columns were dropped so that can be later used during prediction
    # This line just compares the two column indices and finds the differences
    badCols = list(set(df.columns) - set(output.columns))
    db.Prediction('badCols').put(badCols)
    return output


def learn(X, Y):
    cvfit = cvglmnet(x=X.to_numpy().copy(), y=Y.to_numpy().copy())
    db.Prediction('model').put(cvfit)


# Taken from the glmnet_python library, added a return to it so it can be saved
# Not too important for functionality, just info about the system
def cvglmnetPlotReturn(cvobject, sign_lambda=1.0, **options):
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


def shutdown():
    global shutdownServer
    shutdownServer = True


if __name__ == '__main__':
    runLearning()
