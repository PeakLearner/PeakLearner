import json

import numpy as np
import time

import berkeleydb
import logging
import pandas as pd

from core.Handlers import Tracks
from core.Models import Models
from simpleBDB import retry, txnAbortOnError
from core.util import PLdb as db, PLConfig as cfg

log = logging.getLogger(__name__)

statuses = ['New', 'Queued', 'Processing', 'Done', 'Error', 'NoData']


class JobType(type):
    """Just a simple way to keep track of different job types without needing to do it manually"""
    jobTypes = {}

    def __init__(cls, name, bases, dct):
        """Adds everything but the base job type to the jobTypes list"""
        if hasattr(cls, 'jobType'):
            cls.jobTypes[cls.jobType] = cls

    def fromStorable(cls, storable):
        """Create a job type from a storable object

        These storables are dicts which are stored using the Job type in api.util.PLdb
        """

        if 'jobType' not in storable:
            return None

        storableClass = cls.jobTypes[storable['jobType']]
        return storableClass.withStorable(storable)


class Job(metaclass=JobType):
    """Class for storing job information"""

    jobType = 'job'

    def __init__(self, user, hub, track, problem, priority, trackUrl=None, tasks=None):
        self.user = str(user)
        self.hub = hub
        self.track = track
        self.problem = problem
        self.priority = int(priority)

        if tasks is None:
            self.tasks = {}
        else:
            self.tasks = tasks

        # When adding labels during hub upload the URL hasn't been stored yet
        if trackUrl is None:
            txn = db.getTxn()
            hubInfo = db.HubInfo(user, hub).get(txn=txn)
            try:
                self.trackUrl = hubInfo['tracks'][track]['url']
            except TypeError:
                log.debug(hubInfo)
                log.debug(db.HubInfo.db_key_tuples())
                log.debug(user, track)
                txn.commit()
                raise Exception
            txn.commit()
        else:
            self.trackUrl = trackUrl
        self.status = 'New'

    @classmethod
    def withStorable(cls, storable):
        """Creates new job using the storable object"""
        # https://stackoverflow.com/questions/2168964/how-to-create-a-class-instance-without-calling-initializer
        self = cls.__new__(cls)
        self.user = str(storable['user'])
        self.hub = storable['hub']
        self.track = storable['track']
        self.problem = storable['problem']
        self.trackUrl = storable['trackUrl']
        self.status = storable['status']
        self.tasks = storable['tasks']
        self.id = str(storable['id'])
        self.iteration = storable['iteration']
        self.priority = int(storable['priority'])
        try:
            self.lastModified = storable['lastModified']
        except KeyError:
            pass
        return self

    def putNewJob(self, txn):
        """puts Job into job list if the job doesn't exist"""

        self.id = str(db.JobInfo('Id').incrementId(txn=txn))

        self.iteration = str(db.Iteration(self.user,
                                          self.hub,
                                          self.track,
                                          self.problem['chrom'],
                                          self.problem['chromStart']).increment(txn=txn))

        self.lastModified = time.time()

        db.Job(self.id).put(self.__dict__(), txn=txn)

        return self.id

    def equals(self, jobToCheck):
        """Check if current job is equal to the job to check"""
        if self.user != jobToCheck.user:
            return False

        if self.hub != jobToCheck.hub:
            return False

        if self.track != jobToCheck.track:
            return False

        if (self.problem['chrom'] != jobToCheck.problem['chrom']
                or int(self.problem['chromStart']) != int(jobToCheck.problem['chromStart'])
                or int(self.problem['chromEnd']) != int(jobToCheck.problem['chromEnd'])):
            return False

        if self.jobType != jobToCheck.jobType:
            return False

        return True

    # TODO: Time prediction for job
    def getNextNewTask(self):
        """Get's the next task which is new"""
        for key in self.tasks.keys():
            task = self.tasks[key]
            if task['status'].lower() == 'new':
                task.status = 'Queued'

    def updateTask(self, task, txn=None):
        """Updates a task given a dict with keys to put/update"""
        taskToUpdate = None
        for key in self.tasks.keys():
            taskToUpdate = self.tasks[key]
            updateId = int(taskToUpdate['taskId'])
            taskId = int(task['taskId'])
            if updateId == taskId:
                break

        if taskToUpdate is None:
            raise Exception

        for key in task.keys():
            taskToUpdate[key] = task[key]

        self.lastModified = time.time()

        self.updateJobStatus(txn=txn)

        return taskToUpdate

    def updateJobStatus(self, txn=None):
        """Update current job status to the min of the task statuses"""
        # A status outside the bounds
        minStatusVal = len(statuses)
        minStatus = self.status
        for key in self.tasks.keys():
            taskToCheck = self.tasks[key]
            status = taskToCheck['status']
            if status == 'Error' or status == 'NoData':
                self.status = status
                return
            statusVal = statuses.index(status)
            if statusVal < minStatusVal:
                minStatusVal = statusVal
                minStatus = status

        self.status = minStatus

        if self.status.lower() == 'done':
            times = []
            for task in self.tasks.values():
                try:
                    times.append(float(task['totalTime']))
                except KeyError:
                    continue

            self.time = str(sum(times))

    def getPriority(self):
        return int(self.priority)

    def resetJob(self):
        self.status = 'New'

        for key in self.tasks.keys():
            task = self.tasks[key]
            task['Status'] = 'New'

        self.lastModified = time.time()

    def restartUnfinished(self):
        restarted = False
        for task in self.tasks.values():
            if 'Done' != task['status'] != 'NoData':
                task['status'] = 'New'
                restarted = True

        print(self.tasks)

        self.updateJobStatus()
        self.lastModified = time.time()
        return restarted

    def getJobModelSumPlaceholder(self):
        out = pd.DataFrame()
        for key in self.tasks.keys():
            task = self.tasks[key]

            if task['type'].lower() == 'model':
                out = out.append(Models.getErrorSeries(task['penalty'], -1, -1), ignore_index=True)

        return out

    def numTasks(self):
        return len(self.tasks.keys())

    def __dict__(self):
        output = {'user': self.user,
                  'hub': self.hub,
                  'track': self.track,
                  'problem': self.problem,
                  'jobType': self.jobType,
                  'status': self.status,
                  'id': self.id,
                  'iteration': self.iteration,
                  'tasks': self.tasks,
                  'trackUrl': self.trackUrl,
                  'priority': int(self.priority)}

        try:
            output['lastModified'] = self.lastModified
        except AttributeError:
            pass

        if self.status.lower() == 'done':
            try:
                output['time'] = self.time
            except AttributeError:
                pass

        return output

    def addJobInfoOnTask(self, task):
        task['user'] = self.user
        task['hub'] = self.hub
        task['track'] = self.track
        task['problem'] = self.problem
        task['iteration'] = self.iteration
        task['jobStatus'] = self.status
        task['id'] = self.id
        task['trackUrl'] = self.trackUrl
        try:
            task['lastModified'] = self.lastModified
        except AttributeError:
            pass

        return task


def createModelTask(taskId, penalty):
    output = {
        'status': 'New',
        'type': 'model',
        'taskId': str(taskId),
        'penalty': str(penalty)
    }

    return output


def createFeatureTask(taskId):
    output = {
        'status': 'New',
        'taskId': str(taskId),
        'type': 'feature'
    }

    return output


class FeatureJob(Job):
    jobType = 'predict'

    def __init__(self, user, hub, track, problem):
        super().__init__(user, hub, track, problem, 0, tasks={'0': createFeatureTask(0)})


class SingleModelJob(Job):
    jobType = 'model'

    def __init__(self, user, hub, track, problem, penalty, priority):
        super().__init__(user, hub, track, problem, priority)
        penalty = round(penalty, 6)
        taskId = str(len(self.tasks.keys()))
        self.tasks[taskId] = createModelTask(taskId, penalty)


class GridSearchJob(Job):
    """"Job type for performing a gridSearch on a region"""
    jobType = 'gridSearch'

    def __init__(self, user, hub, track, problem, penalties, priority, trackUrl=None, tasks=None):
        if tasks is None:
            tasks = {}
        for penalty in penalties:
            taskId = str(len(tasks.keys()))
            penalty = round(penalty, 6)
            tasks[taskId] = createModelTask(taskId, penalty)
        super().__init__(user, hub, track, problem, priority, trackUrl=trackUrl, tasks=tasks)


class PregenJob(GridSearchJob):
    """Grid Search but generate a feature vec"""
    jobType = 'pregen'

    def __init__(self, user, hub, track, problem, penalties, priority, trackUrl=None, tasks=None):
        if tasks is None:
            tasks = {}

        tasks['0'] = createFeatureTask(0)

        super().__init__(user, hub, track, problem, penalties, priority, trackUrl=trackUrl, tasks=tasks)

    def putNewJob(self, txn):
        # Put placeholder features
        featureKey = (self.user,
                      self.hub,
                      self.track,
                      self.problem['chrom'],
                      self.problem['chromStart'])
        db.Features(*featureKey).put(pd.Series(), txn)

        return super().putNewJob(txn)


timeUntilRestart = 3600


@retry
@txnAbortOnError
def checkRestartJobs(data, txn=None):
    jobKeys = db.Job.db_key_tuples()

    currentTime = time.time()

    for key in jobKeys:
        jobTxn = db.getTxn(parent=txn)
        jobDb = db.Job(*key)
        jobToCheck = jobDb.get(txn=jobTxn, write=True)

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
    else:
        jobDb.put(jobToUpdate, txn=txn)

    task = jobToUpdate.addJobInfoOnTask(task)

    return task


@retry
@txnAbortOnError
def getJob(data, txn=None):
    """Gets job by ID"""
    output = db.Job(data['id']).get(txn=txn).__dict__()
    return output


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
    numJobs = newJobs = queuedJobs = processingJobs = doneJobs = 0

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
              'jobs': jobs,
              'avgTime': avgTime}

    return output


@retry
@txnAbortOnError
def spawnJobs(data, txn=None):
    log.info('spawnJobs')
    for job in db.Job.all(txn=txn):
        if job.status.lower() == 'new':
            return
    numJobs = getNoCorrectModelsJobs(txn=txn)

    numJobs = checkForPredictJobs(numJobs, txn=txn)

    log.info('number of jobs spawned: %s' % numJobs)


def getNoCorrectModelsJobs(txn=None):
    modelSumCursor = db.ModelSummaries.getCursor(txn, bulk=True)

    numJobs = 0

    currentSum = modelSumCursor.next()

    while currentSum is not None:
        key, modelSum = currentSum

        # These values are checked due to how Models::getErrorSeries works
        errorModels = modelSum[modelSum['numPeaks'] == -1]
        processingModels = errorModels[errorModels['errors'] == -1]

        if len(processingModels.index) > 0:
            currentSum = modelSumCursor.next()
            continue

        job = jobToRefine(key, modelSum, txn=txn)

        if job is not None:
            placeHolder = job.getJobModelSumPlaceholder()

            modelSumCursor.put(key, addModelSummaries(modelSum, placeHolder))

            job.putNewJob(txn=txn)

            numJobs += 1

        if numJobs >= cfg.maxJobsToSpawn:
            break

        currentSum = modelSumCursor.next()

    modelSumCursor.close()

    return numJobs


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
                if db.Features.has_key(featureKey, txn=txn):
                    if db.ModelSummaries.has_key(featureKey, txn=txn):
                        continue
                    feature = db.Features(*featureKey).get(txn=txn)
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

    return notInAdd.append(toAdd, ignore_index=True)


def checkForSum(row, df):
    return row['penalty'] in df['penalty']


def jobToRefine(key, modelSums, txn=None):
    user, hub, track, ref, start = key

    data = {'user': user, 'hub': hub, 'track': track}

    genome = db.HubInfo(user, hub).get(txn=txn)['genome']

    problems = db.Problems(genome).get(txn=txn)

    chrom = problems[problems['chrom'] == ref]
    start = chrom[chrom['chromStart'] == int(start)]

    problem = start.to_dict('records')[0]

    minError = modelSums[modelSums['errors'] == modelSums['errors'].min()]

    numMinErrors = len(minError.index)

    regions = minError['regions'].max()

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

            # Temporary restriction to prevent it from generating too many models
            # TODO: Remove this if that's okay
            iteration = db.Iteration(user,
                                     hub,
                                     track,
                                     problem['chrom'],
                                     problem['chromStart']).get(txn=txn)

            if iteration < 5:
                return submitGridSearch(problem, data, minPenalty, maxPenalty, regions)
        return

    elif numMinErrors == 1:
        index = minError.index[0]

        model = minError.iloc[0]

        if model['fp'] > model['fn']:
            try:
                compare = modelSums.iloc[index + 1]
            except IndexError:
                return submitOOMJob(problem, data, model['penalty'], '*', regions, )

            # If the next model only has 1 more peak, not worth searching
            if model['numPeaks'] <= compare['numPeaks'] + 1:
                return
        else:
            try:
                compare = modelSums.iloc[index - 1]
            except IndexError:
                return submitOOMJob(problem, data, model['penalty'], '/', regions)

            # If the previous model is only 1 peak away, not worth searching
            if compare['numPeaks'] + 1 >= model['numPeaks']:
                return

        if abs(compare['numPeaks'] - model['numPeaks']) <= 1:
            return

        if compare['penalty'] > model['penalty']:
            top = compare
            bottom = model
        else:
            top = model
            bottom = compare

        return submitSearch(data, problem, bottom, top, regions, txn=txn)

    return


def submitOOMJob(problem, data, penalty, jobType, regions):
    if jobType == '*':
        penalty = float(penalty) * 10
    elif jobType == '/':
        penalty = float(penalty) / 10
    else:
        print("Invalid OOM Job")
        return

    penalty = round(penalty, 6)

    return SingleModelJob(data['user'],
                          data['hub'],
                          data['track'],
                          problem,
                          penalty,
                          regions)


def submitGridSearch(problem, data, minPenalty, maxPenalty, regions, num=cfg.gridSearchSize):
    minPenalty = float(minPenalty)
    maxPenalty = float(maxPenalty)
    penalties = np.linspace(minPenalty, maxPenalty, num + 2).tolist()[1:-1]
    if 'trackUrl' in data:
        return GridSearchJob(data['user'],
                             data['hub'],
                             data['track'],
                             problem,
                             penalties,
                             regions,
                             trackUrl=data['trackUrl'])

    return GridSearchJob(data['user'],
                         data['hub'],
                         data['track'],
                         problem,
                         penalties,
                         regions)


def submitSearch(data, problem, bottom, top, regions, txn=None):
    topLogPen = np.log10(float(top['penalty']))

    bottomLogPen = np.log10(float(bottom['penalty']))

    logPen = (topLogPen + bottomLogPen) / 2

    penalty = float(10 ** logPen)

    return SingleModelJob(data['user'],
                          data['hub'],
                          data['track'],
                          problem,
                          penalty,
                          regions)


@retry
@txnAbortOnError
def putJobRefresh(data, txn=None):
    db.JobInfo('Id').put(data['Id'])

    for iteration in data['iterations']:
        db.Iteration(iteration['user'], iteration['hub'], iteration['track'], iteration['chrom'], iteration['start']).put(iteration['val'], txn=txn)

    for job in data['jobs']:
        db.Job(job['id']).put(job, txn=txn)

    for job in data['done']:
        db.DoneJob(job['id']).put(job, txn=txn)


if cfg.testing:
    @retry
    @txnAbortOnError
    def makeJobHaveBadTime(data, txn=None):
        jobDb = db.Job('0')
        job = jobDb.get(txn=txn, write=True)

        job.lastModified = 0
        job.status = 'Queued'

        jobDb.put(job.__dict__(), txn=txn)


    @retry
    @txnAbortOnError
    def makeNoDataJob(data, txn=None):
        jobDb = db.Job('0')
        job = jobDb.get(txn=txn, write=True)

        job.lastModified = 0
        job.status = 'NoData'
        job.tasks['0']['status'] = 'NoData'

        jobDb.put(job.__dict__(), txn=txn)
