import os
import json
import datetime
import shutil

import berkeleydb
import numpy as np
import pandas as pd
import simpleBDB as db
from core.Jobs import Jobs
from core.Models import Models
import core.util.PLConfig as cfg
from simpleBDB import AbortTXNException
from core.Permissions import Permissions

dbPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'db')


def clearLocks():
    if os.path.exists(dbPath):  # pragma: no cover
        for file in os.listdir(dbPath):
            if '__db.0' not in file:
                continue
            filePath = os.path.join(dbPath, file)
            print('deleting lock file', filePath)
            os.remove(filePath)
            os.remove(filePath)


def openEnv():
    db.open_env()
    db.createEnvWithDir(dbPath)
    db.setLockDetect()


def openDBs():
    db.open_dbs()


def closeDBObjects():
    db.close_dbs()


def addExitRegister():
    import atexit

    atexit.register(closeDBObjects)


def closeDBs():
    db.close_env()


from datetime import datetime


def doBackup():
    backupDir = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'backup')

    if not os.path.exists(backupDir):
        os.makedirs(backupDir)

    currentBackupDir = os.path.join(backupDir, str(datetime.today().date()))

    if not os.path.exists(currentBackupDir):
        os.makedirs(currentBackupDir)

    db.doBackup(currentBackupDir)


def cleanLogs():
    filesToBackup = db.getLogArchive()

    logBackupDir = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'db_log_backup')

    if not os.path.exists(logBackupDir):
        os.makedirs(logBackupDir)

    if len(filesToBackup) != 0:
        for logFile in filesToBackup:
            logFilePath = os.path.join(dbPath, logFile)
            movePath = os.path.join(logBackupDir, logFile)

            shutil.move(logFilePath, movePath)


def getTxn(parent=None):
    if parent is not None:
        return db.getEnvTxn(parent=parent)
    return db.getEnvTxn()


class Model(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")

    def make_details(self):
        return None

    def getInBounds(self, chrom, start, end, txn=None):
        model = self.get(txn=txn)

        if model.index.dtype == 'object':
            model = model.sort_values('chromStart', ignore_index=True)

        return checkInBounds_new(model, chrom, start, end)

    pass


class Loss(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")

    pass


# TODO: Add chrom as key, would lead to speed increases
class Problems(db.PandasDf):
    keys = ("Genome",)

    def getInBounds(self, chrom, start, end, txn=None):
        problems = self.get(txn=txn)

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

    def incrementId(self, txn=None):
        current = self.get(txn=txn, write=True)

        incremented = current + 1

        self.put(incremented, txn=txn)

        return current

    pass


class Job(db.Resource):
    keys = ("ID",)

    def make_details(self):
        return {}

    @classmethod
    def getCursor(cls, txn=None, readCommited=False, bulk=False):
        return JobCursor(db.DB.getCursor(cls, txn=txn, readCommited=readCommited, bulk=bulk), cls)

    @classmethod
    def fromStorable(cls, storable):
        return Jobs.Job.fromStorable(db.Resource.fromStorable(storable))

    @classmethod
    def toStorable(cls, data):
        if data is not None:
            if isinstance(data, Jobs.Job):
                data = data.__dict__()

            return db.Resource.toStorable(data)
        return None

    pass


class DoneJob(Job):
    pass


class NoDataJob(Job):
    pass


class JobCursor(db.Cursor):
    def __init__(self, cursor, parent):
        super().__init__(cursor.cursor, parent)

    def dup(self, flags=berkeleydb.db.DB_POSITION):
        cursor = db.Cursor.dup(self, flags=flags)
        return JobCursor(cursor, Job)


def labelCompare(item, df):
    startSame = item['chromStart'] == df['chromStart']

    endSame = item['chromEnd'] == df['chromEnd']

    return startSame & endSame


class Labels(db.PandasDf):
    keys = ("user", "hub", "track", "chrom")

    def conditional(self, item, df):
        return labelCompare(item, df)

    def sortDf(self, df):
        df['floatStart'] = df['chromStart'].astype(float)

        df = df.sort_values('floatStart', ignore_index=True)

        return df.drop(columns='floatStart')

    def getInBounds(self, chrom, start, end, txn=None, write=False):
        labels = self.get(txn=txn, write=write)

        if labels is None:
            return None
        if len(labels.index) < 1:
            return labels

        if labels.index.dtype == 'object':
            labels = labels.sort_values('chromStart', ignore_index=True)

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


# https://stackoverflow.com/questions/67593037/what-is-an-efficient-method-using-pandas-for-retrieving-data-with-a-given-start
def checkInBounds_new(df, chrom, chromStart, chromEnd):
    bound1 = df.chromStart.searchsorted(chromStart)
    bound2 = df.chromStart.searchsorted(chromEnd)

    df = df.loc[bound1:bound2]

    return df[df['chrom'] == chrom]


class NeedMoreModels(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def make_details(self):
        return 0

    def add(self, txn=None):
        val = self.get(txn=txn, write=True) + 1

        self.put(val, txn=txn)

        return val

    pass


class ModelSummaries(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def conditional(self, item, df):
        return item['penalty'] == df['penalty']

    def sortDf(self, df):
        df['floatPenalty'] = df['penalty'].astype(float)

        df = df.sort_values('floatPenalty', ignore_index=True)

        return df.drop(columns='floatPenalty')

    def put(self, value, txn=None):
        # If no 0 error models
        if not (value['errors'] == 0).any():
            # If no uncalculated models
            if not (value['errors'] == -1).any():
                NeedMoreModels(*self.values).add(txn=txn)
            else:
                if NeedMoreModels.has_key(self.values, txn=txn, write=True):
                    NeedMoreModels(*self.values).put(None, txn=txn)

        return db.PandasDf.put(self, self.sortDf(value), txn=txn)

    def add_item(self, df):
        out = db.PandasDf.add_item(self, df)

        return self.sortDf(out)


    pass


class Features(db.Resource):
    keys = ("user", "hub", "track", "chrom", "chromStart")

    def make_details(self):
        return {}

    pass


class NoPrediction(Features):
    pass


class HubInfo(db.Resource):
    keys = ("User", "Hub")

    def make_details(self):
        return None

    pass


class Prediction(db.Resource):
    keys = ("Key",)

    def make_details(self):
        return 0

    def increment(self, txn=None):
        current = self.get(txn=txn, write=True)

        incremented = current + 1

        self.put(incremented, txn=txn)

        return current

    pass


class Iteration(db.Resource):
    keys = ("user", "hub", "track", "chrom", "chromStart")

    def make_details(self):
        return 0

    def increment(self, txn=None):
        current = self.get(txn=txn, write=True)

        incremented = current + 1

        self.put(incremented, txn=txn)

        return current


class Permission(db.Resource):
    keys = ("user", "hub")

    @classmethod
    def getCursor(cls, txn=None, readCommited=False, bulk=False):
        return PermissionsCursor(db.DB.getCursor(cls, txn=txn, readCommited=readCommited, bulk=bulk), cls)

    @classmethod
    def fromStorable(cls, storable):
        return Permissions.Permission.fromStorable(db.Resource.fromStorable(storable))

    @classmethod
    def toStorable(cls, data):
        if data is not None:
            if isinstance(data, list):
                return db.Resource.toStorable(data)
            elif not isinstance(data, dict):
                data = data.__dict__()

            return db.Resource.toStorable(data)
        return None

    pass


class PermissionsCursor(db.Cursor):
    def __init__(self, cursor, parent):
        super().__init__(cursor.cursor, parent)

    def dup(self, flags=berkeleydb.db.DB_POSITION):
        cursor = db.Cursor.dup(self, flags=flags)
        return PermissionsCursor(cursor, Permissions)
