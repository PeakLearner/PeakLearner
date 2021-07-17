import os
import json
import datetime
import berkeleydb
import pandas as pd
import simpleBDB as db
from core.Jobs import Jobs
from core.Models import Models
import core.util.PLConfig as cfg
from simpleBDB import AbortTXNException
from core.Permissions import Permissions

dbPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'db')

loaded = False


def isLoaded():
    return loaded


# Remove locks if they are left over
if not loaded:
    if os.path.exists(dbPath):  # pragma: no cover
        for file in os.listdir(dbPath):
            if '__db.0' not in file:
                continue
            filePath = os.path.join(dbPath, file)
            print('deleting lock file', filePath)
            os.remove(filePath)


def openDBs():
    global loaded
    print('opening db')
    db.open_env()
    db.createEnvWithDir(dbPath)
    db.open_dbs()
    loaded = True


def closeDBs(closeEnv=True):
    global loaded
    loaded = False
    db.close_dbs()
    db.close_env()


def deadlock_detect():
    if loaded:
        db.lockDetect()


loadLater = False
try:  # pragma: no cover
    import uwsgi
    import uwsgidecorators

    uwsgi.atexit = closeDBs

    @uwsgidecorators.postfork
    def doOpen():
        openDBs()
        loaded = True

    # run lock detect every second
    @uwsgidecorators.timer(1, target='mule')
    def start_lock_detect(num):
        deadlock_detect()


except ModuleNotFoundError:
    loadLater = True
    print('Running in non uwsgi mode, deadlocks won\'t be detected automatically')


def getTxn(parent=None):
    if parent is not None:
        return db.getEnvTxn(parent=parent)
    return db.getEnvTxn()


class Model(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")

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

    def getInBounds(self, chrom, start, end, txn=None):
        labels = self.get(txn=txn)

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


class ModelSummaries(db.PandasDf):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def conditional(self, item, df):
        return item['penalty'] == df['penalty']

    def sortDf(self, df):
        df['floatPenalty'] = df['penalty'].astype(float)

        df = df.sort_values('floatPenalty', ignore_index=True)

        return df.drop(columns='floatPenalty')

    def fileToStorable(self, filePath):
        df = pd.read_csv(filePath, sep='\t', dtype={'penalty': str})
        return df

    pass


class Features(db.Resource):
    keys = ("user", "hub", "track", "chrom", "chromStart")

    def make_details(self):
        return {}

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
            if not isinstance(data, dict):
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


if loadLater:
    db.open_env()
    db.createEnvWithDir(dbPath)
    openDBs()
