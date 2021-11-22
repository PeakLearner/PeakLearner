import json

import numpy as np
import time

import berkeleydb
import logging
import pandas as pd

from core.Handlers import Tracks
from core.Models import Models
from simpleBDB import retry, txnAbortOnError
from core.util import PLConfig as cfg
from sqlalchemy.orm import Session
from fastapi import Depends
import core
from core import models, dbutil

log = logging.getLogger(__name__)

statuses = ['New', 'Queued', 'Processing', 'Done', 'Error', 'NoData']
peakSegDiskPrePenalties = [1000, 10000, 100000, 1000000]


def createJobForRegion(contigId, db: Session = Depends(core.get_db)):
    """Checks a contig to see if a job can be spawned, if so spawn the job"""
    contig = db.query(models.Contig).get(contigId)

    numJobs = contig.jobs.count()

    if numJobs != 0:
        return

    modelSum = contig.getModelSums(db, withLoss=False)

    return jobToRefine(db, contig, modelSum)


def jobToRefine(db: Session, contig, modelSums):
    minError = modelSums[modelSums['errors'] == modelSums['errors'].min()]

    numMinErrors = len(minError.index)

    if numMinErrors == 0:
        return

    if minError.iloc[0]['errors'] == 0:
        return

    if numMinErrors > 1:
        # no need to generate new models if error is 0
        first = minError.iloc[0]
        last = minError.iloc[-1]

        biggerFp = first['fp'] > last['fp']
        smallerFn = first['fn'] < last['fn']

        # Sanity check for bad labels, if the minimum is still the same values
        # With little labels this could not generate new models
        if biggerFp or smallerFn:
            minPenalty = first['penalty']
            maxPenalty = last['penalty']

            return submitGridSearch(db, contig, minPenalty, maxPenalty)
        return

    elif numMinErrors == 1:
        index = minError.index[0]

        model = minError.iloc[0]

        if model['fp'] > model['fn']:
            try:
                compare = modelSums.iloc[index + 1]
            except IndexError:
                return submitOOMJob(db, contig, model['penalty'], '*')

            # If the next model only has 1 more peak, not worth searching
            if model['numPeaks'] <= compare['numPeaks'] + 1:
                return
        else:
            try:
                compare = modelSums.iloc[index - 1]
            except IndexError:
                return submitOOMJob(db, contig, model['penalty'], '/')

            # If the previous model is only 1 peak away, not worth searching
            if compare['numPeaks'] + 1 >= model['numPeaks']:
                return

        if abs(compare['numPeaks'] - model['numPeaks']) <= 1:
            return

        if float(compare['penalty']) > float(model['penalty']):
            top = compare
            bottom = model
        else:
            top = model
            bottom = compare

        return submitSearch(db, contig, bottom, top)

    return


def submitJob(db: Session, contig, tasks):
    contig.iteration += 1
    job = models.Job(contig=contig.id)
    db.add(job)
    db.flush()
    db.refresh(job)

    for task in tasks:
        task = models.Task(**task, job=job.id)
        db.add(task)
        db.flush()
        db.refresh(task)
    return True


def submitOOMJob(db: Session, contig, penalty, jobType):
    if jobType == '*':
        penalty = float(penalty) * 10
    elif jobType == '/':
        penalty = float(penalty) / 10
    else:
        print("Invalid OOM Job")
        return

    penalty = round(penalty, 6)

    task = [{'taskType': 'model', 'penalty': penalty}]

    return submitJob(db,
                     contig,
                     task)


def submitGridSearch(db, contig, minPenalty, maxPenalty, num=cfg.gridSearchSize):
    minPenalty = float(minPenalty)
    maxPenalty = float(maxPenalty)
    penalties = np.linspace(minPenalty, maxPenalty, num + 2).tolist()[1:-1]

    tasks = []

    for penalty in penalties:
        task = {'taskType': 'model', 'penalty': penalty}
        tasks.append(task)

    return submitJob(db, contig, tasks)


def submitSearch(db, contig, bottom, top):
    topLogPen = np.log10(float(top['penalty']))

    bottomLogPen = np.log10(float(bottom['penalty']))

    logPen = (topLogPen + bottomLogPen) / 2

    penalty = float(10 ** logPen)

    tasks = [{'penalty': penalty, 'taskType': 'model'}]

    return submitJob(db, contig, tasks)


def submitPregenJob(db, contig):
    tasks = [{'taskType': 'feature'}]

    for penalty in peakSegDiskPrePenalties:
        task = {'taskType': 'model', 'penalty': penalty}
        tasks.append(task)

    return submitJob(db, contig, tasks)


def submitFeatureJob(db, contig):
    return submitJob(db, contig, [{'taskType': 'feature'}])


@retry
@txnAbortOnError
def checkRestartJobs(data, txn=None):
    jobKeys = db.Job.db_key_tuples()

    currentTime = time.time()

    for key in jobKeys:
        jobTxn = db.getTxn(parent=txn)
        jobDb = db.Job(*key)
        jobToCheck = jobDb.get(txn=jobTxn, write=True)

        if jobToCheck.status.lower() == 'nodata':
            jobDb.put(None, txn=jobTxn)
            db.NoDataJob(*key).put(jobToCheck, txn=jobTxn)
            jobTxn.commit()
            continue

        try:
            timeDiff = currentTime - jobToCheck.lastModified
        except AttributeError:
            jobToCheck.lastModified = time.time()
            jobDb.put(jobToCheck, txn=jobTxn)
            jobTxn.commit()
            continue

        if timeDiff > timeUntilRestart:
            jobToCheck.restartUnfinished()
            jobDb.put(jobToCheck, txn=jobTxn)
            jobTxn.commit()
            continue

        jobTxn.abort()


@retry
@txnAbortOnError
def resetJob(data, txn=None):
    """resets a job to a new state"""
    jobId = data['jobId']
    jobDb = db.Job(jobId)
    jobToReset = jobDb.get(txn=txn, write=True)
    if isinstance(jobToReset, dict):
        return
    jobToReset.resetJob()
    jobDb.put(jobToReset, txn=txn)
    return jobToReset.__dict__()


@retry
@txnAbortOnError
def restartJob(data, txn=None):
    jobId = data['jobId']
    jobDb = db.Job(jobId)
    jobToRestart = jobDb.get(txn=txn, write=True)
    if isinstance(jobToRestart, dict):
        return
    restarted = jobToRestart.restartUnfinished()
    if restarted:
        jobDb.put(jobToRestart, txn=txn)
        return jobToRestart


@retry
@txnAbortOnError
def updateTask(data, txn=None):
    """Updates a task given the job/task id and stuff to update it with"""
    jobId = data['id']
    task = data['task']

    jobDb = db.Job(jobId)
    jobToUpdate = jobDb.get(txn=txn, write=True)
    task = jobToUpdate.updateTask(task, txn=txn)
    if jobToUpdate.status.lower() == 'done':
        jobDb.put(None, txn=txn)
        db.DoneJob(jobId).put(jobToUpdate, txn=txn)
    elif jobToUpdate.status.lower() == 'nodata':
        jobDb.put(None, txn=txn)
        db.NoDataJob(jobId).put(jobToUpdate, txn=txn)
    else:
        jobDb.put(jobToUpdate, txn=txn)

    task = jobToUpdate.addJobInfoOnTask(task)

    return task


@retry
@txnAbortOnError
def queueNextTask(data, txn=None):
    db.Job.syncDb()

    cursor = db.Job.getCursor(txn=txn, bulk=True)

    job, key, cursorAtBest = getJobWithHighestPriority(cursor)

    if job is None:
        return

    key = getNextTaskInJob(job)

    taskToUpdate = job.tasks[key]

    taskToUpdate['status'] = 'Queued'

    job.updateJobStatus()

    cursorAtBest.put(key, job)

    cursorAtBest.close()

    task = job.addJobInfoOnTask(taskToUpdate)

    return task


def getJobWithHighestPriority(cursor):
    jobWithTask = None
    keyWithTask = None
    cursorAtBest = None

    current = cursor.next(flags=berkeleydb.db.DB_RMW)

    while current is not None:
        key, job = current

        if job.status.lower() == 'new':
            if jobWithTask is None:
                jobWithTask = job
                keyWithTask = key
                cursorAtBest = cursor.dup()

            elif jobWithTask.getPriority() < job.getPriority():
                jobWithTask = job
                keyWithTask = key
                cursorAtBest.close()
                cursorAtBest = cursor.dup()

        current = cursor.next(flags=berkeleydb.db.DB_RMW)

    cursor.close()
    return jobWithTask, keyWithTask, cursorAtBest


def getNextTaskInJob(job):
    tasks = job.tasks
    for key in tasks.keys():
        task = tasks[key]

        if task['status'].lower() == 'new':
            return key


@retry
@txnAbortOnError
def getAllJobs(data, txn=None):
    jobs = []

    cursor = db.Job.getCursor(txn, bulk=True)

    try:
        current = cursor.next()

        while current is not None:
            key, job = current

            jobs.append(job.__dict__())

            current = cursor.next()
    except berkeleydb.db.DBLockDeadlockError:
        cursor.close()
        raise

    cursor.close()

    return jobs


@retry
@txnAbortOnError
def getJobWithId(data, txn=None):
    job = db.Job(data['jobId']).get(txn=txn)

    if isinstance(job, dict):
        job = db.DoneJob(data['jobId']).get(txn=txn)

        if isinstance(job, dict):
            job = db.NoDataJob(data['jobId']).get(txn=txn)

    if isinstance(job, dict):
        return job

    output = job.__dict__()

    output['jobUser'] = output['user']

    return output


@retry
@txnAbortOnError
def getTrackJobs(data, txn=None):
    problems = Tracks.getProblems(data, txn=txn)

    cursor = db.Job.getCursor(txn, bulk=True)

    jobs = jobsWithCursor(cursor, data, problems)

    cursor.close()

    doneJobCursor = db.DoneJob.getCursor(txn, bulk=True)

    jobs.extend(jobsWithCursor(doneJobCursor, data, problems))

    doneJobCursor.close()

    return jobs


def jobsWithCursor(cursor, data, problems):
    jobs = []

    current = cursor.next()

    while current is not None:

        key, job = current

        if data['user'] != job.user:
            current = cursor.next()
            continue

        if data['hub'] != job.hub:
            current = cursor.next()
            continue

        if data['track'] != job.track:
            current = cursor.next()
            continue

        jobProblem = job.problem

        if jobProblem['chrom'] != data['ref']:
            current = cursor.next()
            continue

        toAppend = False

        for problem in problems:
            if jobProblem['chromStart'] == problem['chromStart']:
                toAppend = True

        if toAppend:
            jobs.append(job.__dict__())

        current = cursor.next()

    return jobs


@retry
@txnAbortOnError
def jobsStats(data, txn=None):
    numJobs = newJobs = queuedJobs = processingJobs = doneJobs = noDataJobs = errorJobs = 0

    times = []

    jobs = []
    for job in db.Job.all(txn=txn):
        numJobs = numJobs + 1
        status = job.status.lower()

        if status == 'new':
            newJobs = newJobs + 1
        elif status == 'queued':
            queuedJobs = queuedJobs + 1
        elif status == 'processing':
            processingJobs = processingJobs + 1
        elif status == 'done':
            doneJobs = doneJobs + 1
        elif status == 'nodata':
            noDataJobs = noDataJobs + 1
        elif status == 'error':
            noDataJobs = noDataJobs + 1

            for task in job.tasks.values():
                if task['status'].lower() == 'done':
                    times.append(float(task['totalTime']))

        if status != 'done':
            jobs.append(job.__dict__())

    if len(times) == 0:
        avgTime = 0
    else:
        avgTime = str(sum(times) / len(times))

    output = {'numJobs': numJobs,
              'newJobs': newJobs,
              'queuedJobs': queuedJobs,
              'processingJobs': processingJobs,
              'doneJobs': doneJobs,
              'noDataJobs': noDataJobs,
              'errorJobs': errorJobs,
              'jobs': jobs,
              'avgTime': avgTime,
              'errorRegions': len(db.NeedMoreModels.db_keys())}

    return output


@retry
@txnAbortOnError
def spawnJobs(data, txn=None):
    log.info('spawnJobs')
    for job in db.Job.all(txn=txn):
        if job.status.lower() == 'new':
            return

    numJobs = checkForPredictJobs(numJobs, txn=txn)

    log.info('number of jobs spawned: %s' % numJobs)


def checkForPredictJobs(numJobs, txn=None):
    hubInfoCursor = db.HubInfo.getCursor(txn=txn, bulk=True)

    current = hubInfoCursor.next()

    while current is not None:
        key, hubInfo = current

        user, hub = key

        problems = db.Problems(hubInfo['genome']).get(txn=txn)

        for track in hubInfo['tracks']:
            for problemRowKey, row in problems.iterrows():
                featureKey = (user, hub, track, row['chrom'], str(row['chromStart']))

                # If the feature already exists, then make a single model job
                if db.Features.has_key(featureKey, txn=txn, write=True):
                    if db.ModelSummaries.has_key(featureKey, txn=txn):
                        continue
                    feature = db.Features(*featureKey).get(txn=txn)
                    if isinstance(feature, str):
                        continue
                    if len(feature.keys()) < 1:
                        # The feature vec is currently being processed
                        continue

                    predictionModel = db.Prediction('model').get(txn=txn)

                    # Prediction not yet available
                    if not isinstance(predictionModel, dict):
                        continue

                    colsToDrop = db.Prediction('badCols').get(txn=txn)

                    featuresDropped = feature.drop(labels=colsToDrop)

                    prediction = Models.predictWithFeatures(featuresDropped, predictionModel)

                    if prediction is None:
                        continue

                    penaltyToUse = round(float(10 ** prediction), 6)

                    job = SingleModelJob(user, hub, track, row.to_dict(), penaltyToUse, 0)

                    job.putNewJob(txn=txn)

                    placeHolder = job.getJobModelSumPlaceholder()

                    db.ModelSummaries(user, hub, track, row['chrom'], row['chromStart']).add(placeHolder, txn=txn)

                    numJobs += 1
                else:
                    outputJob = FeatureJob(user, hub, track, row.to_dict())

                    outputJob.putNewJob(txn=txn)

                    db.Features(*featureKey).put(pd.Series(), txn)

                    numJobs += 1

                if numJobs >= cfg.maxJobsToSpawn:
                    break
            if numJobs >= cfg.maxJobsToSpawn:
                break
        if numJobs >= cfg.maxJobsToSpawn:
            break
        current = hubInfoCursor.next()

    hubInfoCursor.close()

    return numJobs


def addModelSummaries(main, toAdd):
    main['inAdd'] = main.apply(checkForSum, axis=1, args=(toAdd,))

    notInAdd = main[~main['inAdd']].drop(columns='inAdd')

    df = notInAdd.append(toAdd, ignore_index=True)

    df['floatPenalty'] = df['penalty'].astype(float)

    df = df.sort_values('floatPenalty', ignore_index=True)

    return df.drop(columns='floatPenalty')


def checkForSum(row, df):
    return row['penalty'] in df['penalty']


@retry
@txnAbortOnError
def putJobRefresh(data, txn=None):
    db.JobInfo('Id').put(data['Id'])

    for iteration in data['iterations']:
        db.Iteration(iteration['user'], iteration['hub'], iteration['track'], iteration['chrom'],
                     iteration['start']).put(iteration['val'], txn=txn)

    for job in data['jobs']:
        db.Job(job['id']).put(job, txn=txn)

    for job in data['done']:
        db.DoneJob(job['id']).put(job, txn=txn)
