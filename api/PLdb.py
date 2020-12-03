import os
import pickle
import pandas as pd
import api.PLConfig as cfg
import simpleBDB as db


dbPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'db')

db.createEnvWithDir(dbPath)


def close():
    db.close_db()


class Model(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")
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

        print('jobs before add/update\n', jobs, '\n')
        newJobs, updated = self.updateExisting(jobs)
        if not updated:
            self.createNewJobWithItem()
            jobs.append(self.item)
            print('jobs after initial add\n', jobs, '\n')
            return jobs
        print('jobs after update\n', newJobs, '\n')
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
        return job[index] == self.item[index]

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

    pass


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


def updateSummaryInDf(row, item):
    if row['penalty'] == item['penalty']:
        return item
    return row
