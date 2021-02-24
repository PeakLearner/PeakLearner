from api.util import PLdb as db
from api.Handlers.Handler import Handler
from api.Handlers import Models


statuses = ['New', 'Queued', 'Processing', 'Done', 'Error']


class JobHandler(Handler):
    """Handles Job Commands"""

    def do_POST(self, data):
        funcToRun = self.getCommands()[data['command']]
        args = {}
        if 'args' in data:
            args = data['args']
            
        return funcToRun(args)

    @classmethod
    def getCommands(cls):
        # TODO: Add update/delete/info
        return {'get': getJob,
                'getAll': getAllJobs,
                'update': updateTask,
                'reset': resetJob,
                'resetAll': resetAllJobs,
                'nextTask': startNextTask,
                'check': checkNewTask}


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

    def __init__(self, user, hub, track, problem, trackUrl=None, tasks=None):
        self.user = user
        self.hub = hub
        self.track = track
        self.problem = problem

        if tasks is None:
            self.tasks = {}
        else:
            self.tasks = tasks

        # When adding labels during hub upload the URL hasn't been stored yet
        if trackUrl is None:
            txn = db.getTxn()
            hubInfo = db.HubInfo(user, hub).get(txn=txn)
            try:
                self.trackUrl = hubInfo['tracks'][track]
            except TypeError:
                print(hubInfo)
                print(db.HubInfo.db_key_tuples())
                print(user, track)
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
        self.user = storable['user']
        self.hub = storable['hub']
        self.track = storable['track']
        self.problem = storable['problem']
        self.trackUrl = storable['trackUrl']
        self.status = storable['status']
        self.tasks = storable['tasks']
        self.id = storable['id']
        self.iteration = storable['iteration']
        return self

    def putNewJob(self):
        """puts Job into job list if the job doesn't exist"""

        txn = db.getTxn()
        if self.checkIfExists(txn=txn):
            txn.commit()
            return

        self.id = str(db.JobInfo('Id').incrementId(txn=txn))
        self.iteration = db.Iteration(self.user,
                                      self.hub,
                                      self.track,
                                      self.problem['chrom'],
                                      self.problem['chromStart']).increment(txn=txn)

        self.putWithDb(db.Job(self.id), txn=txn)
        txn.commit()

        return self.id

    def checkIfExists(self, txn=None):
        """Check if the current job exists in the DB"""
        for keys in db.Job.db_key_tuples():
            jobToCheck = db.Job(*keys).get(txn=txn)

            if jobToCheck is None:
                continue

            if self.equals(jobToCheck):
                return True

        return False

    def equals(self, jobToCheck):
        """Check if current job is equal to the job to check"""
        if self.user != jobToCheck.user:
            return False

        if self.hub != jobToCheck.hub:
            return False

        if self.track != jobToCheck.track:
            return False

        if self.problem != jobToCheck.problem:
            return False

        return True

    # TODO: Time prediction for job
    def getNextNewTask(self):
        """Get's the next task which is new"""
        for key in self.tasks.keys():
            task = self.tasks[key]
            if task['status'].lower() == 'new':
                task.status = 'Queued'

    def updateTask(self, task):
        """Updates a task given a dict with keys to put/update"""
        taskToUpdate = None
        for key in self.tasks.keys():
            taskToUpdate = self.tasks[key]
            if taskToUpdate['taskId'] == task['taskId']:
                break

        if taskToUpdate is None:
            raise Exception

        for key in task.keys():
            taskToUpdate[key] = task[key]

        self.updateJobStatus(taskToUpdate)
            
        return self.addJobInfoOnTask(taskToUpdate)

    def updateJobStatus(self, task):
        """Update current job status to the min of the task statuses"""
        # A status outside the bounds
        minStatusVal = len(statuses)
        minStatus = self.status
        for key in self.tasks.keys():
            taskToCheck = self.tasks[key]
            status = taskToCheck['status']
            if status == 'Error':
                self.status = status
                return
            statusVal = statuses.index(status)
            if statusVal < minStatusVal:
                minStatusVal = statusVal
                minStatus = status

        currentStatusVal = statuses.index(self.status)

        if currentStatusVal < minStatusVal:
            self.status = minStatus

    def getPriority(self):
        """Eventually will calculate the priority of the job"""
        return 0

    def resetJob(self):
        self.status = 'New'

        for key in self.tasks.keys():
            task = self.tasks[key]
            task['Status'] = 'New'

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
                  'trackUrl': self.trackUrl}

        return output

    def putWithDb(self, jobDb, txn=None):
        toStore = self.__dict__()

        jobDb.put(toStore, txn=txn)

    def addJobInfoOnTask(self, task):
        task['user'] = self.user
        task['hub'] = self.hub
        task['track'] = self.track
        task['problem'] = self.problem
        task['iteration'] = self.iteration
        task['id'] = self.id
        task['trackUrl'] = self.trackUrl

        return task


def createModelTask(taskId, penalty):
    output = {
        'status': 'New',
        'type': 'model',
        'taskId': taskId,
        'penalty': penalty
    }

    return output


def createFeatureTask(taskId):
    output = {
        'status': 'New',
        'taskId': str(taskId),
        'type': 'feature'
    }

    return output


class PredictJob(Job):
    jobType = 'predict'

    def __init__(self, user, hub, track, problem):
        super().__init__(user, hub, track, problem, tasks={'0', createFeatureTask(0)})

    def updateJobStatus(self, task):
        if task['taskId'] == '0':
            if task['status'] == 'Done':
                # Get Predicition Penalty
                # Submit SingleModelJob with penalty
                print()

        Job.updateJobStatus(self, task)


class SingleModelJob(Job):
    jobType = 'model'

    def __init__(self, user, hub, track, problem, penalty):
        super().__init__(user, hub, track, problem)
        taskId = str(len(self.tasks.keys()))
        self.tasks[taskId] = createModelTask(taskId, penalty)


class GridSearchJob(Job):
    """"Job type for performing a gridSearch on a region"""
    jobType = 'gridSearch'

    def __init__(self, user, hub, track, problem, penalties, trackUrl=None, tasks=None):
        if tasks is None:
            tasks = {}
        for penalty in penalties:
            taskId = str(len(tasks.keys()))
            tasks[taskId] = createModelTask(taskId, penalty)
        super().__init__(user, hub, track, problem, trackUrl=trackUrl, tasks=tasks)

    def equals(self, jobToCheck):
        if not Job.equals(self, jobToCheck):
            return False

        # The penalties are the keys
        if jobToCheck.tasks == self.tasks:
            return True

        return False


class PregenJob(GridSearchJob):
    """Grid Search but generate a feature vec"""
    jobType = 'pregen'

    def __init__(self, user, hub, track, problem, penalties, trackUrl=None, tasks=None):
        if tasks is None:
            tasks = {}

        tasks['0'] = createFeatureTask(0)

        super().__init__(user, hub, track, problem, penalties, trackUrl=trackUrl, tasks=tasks)


def updateTask(data):
    """Updates a task given the job/task id and stuff to update it with"""
    jobId = data['id']
    task = data['task']
    txn = db.getTxn()
    jobDb = db.Job(jobId)
    jobToUpdate = jobDb.get(txn=txn, write=True)
    task = jobToUpdate.updateTask(task)
    jobDb.put(jobToUpdate, txn=txn)
    txn.commit()

    if jobToUpdate.status == 'Done':
        checkForMoreJobs(task, txn=txn)
    return task


def checkForMoreJobs(task, txn=None):
    problem = task['problem']
    modelSums = db.ModelSummaries(task['user'],
                                  task['hub'],
                                  task['track'],
                                  problem['chrom'],
                                  problem['chromStart']).get(txn=txn)
    return Models.checkGenerateModels(modelSums, problem, task)


def resetJob(data):
    """resets a job to a new state"""
    jobId = data['jobId']
    txn = db.getTxn()
    jobDb = db.Job(jobId)
    jobToReset = jobDb.get(txn=txn, write=True)
    jobToReset.resetJob()
    jobDb.put(jobToReset, txn=txn)
    txn.commit()
    return jobToReset.asDict()


def resetAllJobs(data):
    """Resets all jobs"""
    for keys in db.Job.db_key_tuples():
        txn = db.getTxn()
        jobDb = db.Job(*keys)
        jobToReset = jobDb.get(txn=txn, write=True)
        jobToReset.resetJob()
        jobDb.put(jobToReset, txn=txn)
        txn.commit()


def getJob(data):
    """Gets job by ID"""
    return db.Job(data['id']).get().asDict()


def startNextTask(data):
    txn = db.getTxn()
    jobIdWithTask = getJobIdWithHighestPriority(txn=txn)

    jobDb = db.Job(jobIdWithTask)
    jobWithTask = jobDb.get(txn=txn, write=True)

    taskToRun = getNextTaskInJob(jobWithTask)

    if taskToRun is None:
        txn.commit()
        raise Exception(jobWithTask.__dict__())

    taskToRun['status'] = 'Queued'

    jobWithTask.updateTask(taskToRun)

    taskToRun['id'] = jobIdWithTask

    jobDb.put(jobWithTask, txn=txn)
    txn.commit()

    return taskToRun


def getJobIdWithHighestPriority(txn=None):
    jobWithTask = None

    for key in db.Job.db_key_tuples():

        jobDb = db.Job(*key)
        toCheck = jobDb.get(txn=txn)

        if toCheck.status.lower() == 'new':

            if jobWithTask is None:
                jobWithTask = toCheck

            elif toCheck.getPriority() > jobWithTask.getPriority():
                jobWithTask = toCheck
    return jobWithTask.id


def getNextTaskInJob(job):
    tasks = job.tasks
    for key in tasks.keys():
        task = tasks[key]

        if task['status'].lower() == 'new':
            return task

    return None


def checkNewTask(data):
    for keys in db.Job.db_key_tuples():
        jobDb = db.Job(*keys)
        jobToCheck = jobDb.get()

        if jobToCheck.status.lower() == 'new':
            return True
    return False


def getAllJobs(data):
    jobs = []

    txn = db.getTxn()

    for key in db.Job.db_key_tuples():
        value = db.Job(*key).get(txn=txn)
        if value is None:
            continue

        jobs.append(value.__dict__())

    txn.commit()
    return jobs


def stats():
    numJobs = newJobs = queuedJobs = processingJobs = doneJobs = 0

    jobs = []
    txn = db.getTxn()
    for key in db.Job.db_key_tuples():
        job = db.Job(*key).get(txn=txn)
        numJobs = numJobs + 1
        jobs.append(job)
        status = job.status.lower()

        if status == 'new':
            newJobs = newJobs + 1
        elif status == 'queued':
            queuedJobs = queuedJobs + 1
        elif status == 'processing':
            processingJobs = processingJobs + 1
        elif status == 'done':
            doneJobs = doneJobs + 1

    txn.commit()

    output = {'numJobs': numJobs,
              'newJobs': newJobs,
              'queuedJobs': queuedJobs,
              'processingJobs': processingJobs,
              'doneJobs': doneJobs,
              'jobs': jobs}

    return output

