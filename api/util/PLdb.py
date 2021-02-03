import os
import json
import datetime
import api.util.PLConfig as cfg
import simpleBDB as db
import atexit


dbPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'db')

db.createEnvWithDir(dbPath)


def close():
    db.close_db()


def getTxn():
    return db.getEnvTxn()


class Model(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")

    def getInBounds(self, chrom, start, end):
        model = self.get()

        isInBounds = model.apply(checkInBounds, axis=1, args=(chrom, start, end))

        return model[isInBounds]
    pass


class Problems(db.PandasDf):
    keys = ("Genome",)

    def getInBounds(self, chrom, start, end):
        problems = self.get()

        if problems is None:
            return None

        isInBounds = problems.apply(checkInBounds, axis=1, args=(chrom, start, end))

        return problems[isInBounds]

    def make_details(self):
        return None
    pass


class JobInfo(db.Resource):
    keys = ("stat",)

    def make_details(self):
        return 0

    def incrementId(self):
        current = self.get()

        incremented = current + 1

        self.put(incremented)

        return current

    pass


class Job(db.Container):
    keys = ("Key",)

    def make_details(self):
        return []

    def add_item(self, jobs):
        if 'id' not in self.item.keys():
            self.item['id'] = JobInfo('id').get()
        newJobs, updated = self.updateExisting(jobs)
        if not updated:
            self.createNewJobWithItem()
            jobs.append(self.item)
            return jobs
        return newJobs

    def remove_item(self, jobs):
        newJobList = jobs.copy()

        for job in jobs:
            if job['id'] == self.item['id']:
                newJobList.remove(job)
                self.removed = job

        return newJobList

    def updateExisting(self, jobs):
        updated = False
        newJobList = jobs.copy()
        for job in jobs:
            if job['id'] == self.item['id']:
                newJobList.remove(job)
                if not self.checkIfDone():
                    newJobList.append(self.updateJob(job))
                updated = True
            else:
                toCheck = ['user', 'hub', 'track', 'jobType', 'jobData']
                notSame = True
                for check in toCheck:
                    if not self.checkSame(job, check):
                        notSame = False
                        break

                if notSame:
                    newJobList.remove(job)
                    newJobList.append(self.updateJob(job))
                    updated = True

        return newJobList, updated

    def checkSame(self, job, index):
        try:
            return job[index] == self.item[index]
        except KeyError:
            return False

    def updateJob(self, job):
        for key in self.item.keys():
            if key == 'id':
                continue
            job[key] = self.item[key]
        self.item = job
        return job

    def checkIfDone(self):
        if 'status' in self.item.keys():
            if self.item['status'].lower() == 'done':
                return True
        return False

    def createNewJobWithItem(self):
        self.item['status'] = 'New'
        self.item['id'] = JobInfo('id').incrementId()

    pass


class Labels(db.PandasDf):
    keys = ("user", "hub", "track", "chrom")

    def conditional(self, item, df):
        startSame = item['chromStart'] == df['chromStart']

        endSame = item['chromEnd'] == df['chromEnd']
        return startSame & endSame

    def sortDf(self, df):
        df['floatStart'] = df['chromStart'].astype(float)

        df = df.sort_values('floatStart', ignore_index=True)

        return df.drop(columns='floatStart')

    def getInBounds(self, chrom, start, end):
        labels = self.get()

        if labels is None:
            return None
        if len(labels.index) < 1:
            return labels

        isInBounds = labels.apply(checkInBounds, axis=1, args=(chrom, start, end))

        return labels[isInBounds]

    pass


def checkInBounds(row, chrom, chromStart, chromEnd):
    try:
        if not chrom == row['chrom']:
            return False
    except KeyError:
        print('row count', row.count)
        print("CheckInBoundsKeyError\nRow\n", row, '\n chrom', chrom, 'start', chromStart, 'end', chromEnd)
        return False

    if chromStart <= row['chromStart'] <= chromEnd:
        return True
    elif chromStart <= row['chromEnd'] <= chromEnd:
        return True
    else:
        return (row['chromStart'] < chromEnd) and (row['chromEnd'] > chromEnd)


def checkLabelExists(row, dfToCheck):
    duplicate = dfToCheck['chromStart'] == row['chromStart']
    return duplicate.any()


def updateLabelInDf(row, item):
    if row['chromStart'] == item['chromStart']:
        return item
    return row


class ModelSummaries(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def conditional(self, item, df):
        return item['penalty'] == df['penalty']

    def sortDf(self, df):
        df['floatPenalty'] = df['penalty'].astype(float)

        df = df.sort_values('floatPenalty', ignore_index=True)

        return df.drop(columns='floatPenalty')

    pass


class Features(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def make_details(self):
        return {}

    def get(self, txn=None, write=False):
        return json.loads(db.Resource.get(self, txn, write))

    def put(self, value, txn=None):
        db.Resource.put(self, json.dumps(value), txn)

    def convert(self, value, *args):
        return db.Resource.convert(self, value[0])

    pass


def updateSummaryInDf(row, item):
    if row['penalty'] == item['penalty']:
        return item
    return row


class HubInfo(db.Resource):
    keys = ("User", "Hub")

    def make_details(self):
        return None

    pass


backup_restore = [HubInfo, Features, ModelSummaries, Labels, Problems, Model]


def getLastBackup():
    if not os.path.exists(cfg.backupPath):
        return

    last_backup = None
    firstCheck = True

    for backup in os.listdir(cfg.backupPath):
        backupTime = datetime.datetime.strptime(backup, '%Y-%m-%d %H:%M:%S.%f')
        if firstCheck:
            firstCheck = False
            last_backup = backupTime
            continue

        if backupTime > last_backup:
            last_backup = backupTime

    return last_backup


def doBackup(*args):
    if not os.path.exists(cfg.backupPath):
        try:
            os.makedirs(cfg.backupPath)
        except OSError:
            return False

    backupTime = str(datetime.datetime.now())

    currentBackupPath = os.path.join(cfg.backupPath, backupTime)

    if not os.path.exists(currentBackupPath):
        try:
            os.makedirs(currentBackupPath)
        except OSError:
            return False
    for backup in backup_restore:
        backup.doBackup(currentBackupPath, args)

    return True


def doRestore():
    if not os.path.exists(cfg.backupPath):
        return False

    lastBackup = getLastBackup()

    backupPath = os.path.join(cfg.backupPath, str(lastBackup))

    for restore in backup_restore:
        restore.doRestore(backupPath)



    return True




