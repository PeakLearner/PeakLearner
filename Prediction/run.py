import pandas as pd
import numpy as np
import glmnet_python
from glmnet import glmnet
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
                firstStart = False
                lastRun = time.time()
                print('getting datapoints')
                datapoints = getDataPoints()
                print('start learning')
                learn(*datapoints)

                print('stopped learning')
            else:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print('test')
    print('Learning loop stopped')


def check():
    changes = db.Prediction('changes').get()
    if changes > cfg.numChanges:
        if not db.Prediction.has_key('EnoughLabels'):
            db.Prediction('EnoughLabels').put(False)

        if db.Prediction('EnoughLabels').get():
            return True
        else:
            if checkLabelRegions():
                print('enough labels')
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

        if isinstance(features, dict):
            featuresTxn.commit()
            continue

        elif isinstance(features, list):
            if not len(features) == 1:
                raise Exception

            features = features[0]

            featureSeries = pd.Series(features)

            featuresDb.put(featureSeries, txn=featuresTxn)

        elif isinstance(features, pd.Series):
            featureSeries = features

        for penalty in logPenalties:
            datapoint = featureSeries.copy()

            datapoint['logPenalty'] = penalty

            dataPoints = dataPoints.append(datapoint, ignore_index=True)

        featuresTxn.commit()

    # TODO: Save datapoints, update ones which have changed, not all of them every time

    Y = dataPoints['logPenalty']
    X = dataPoints.drop('logPenalty', 1)

    return X, Y


def learn(X, Y):
    #cvfit = cvglmnet(x=X.copy(), y=Y.copy())
    #print(cvfit)
    print(X)



def shutdown():
    global shutdownServer
    shutdownServer = True


def problemToFeatureVec(coverage):
    print(coverage)

runLearning()