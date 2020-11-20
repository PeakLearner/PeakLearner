import os
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


class Labels(db.PandasDf):
    keys = ("user", "hub", "track", "chrom")

    def conditional(self, item, df):
        startSame = item['chromStart'] == df['chromStart']

        endSame = item['chromEnd'] == df['chromEnd']
        return startSame | endSame

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
        return item['chromStart'] == df['chromStart']

    def sortDf(self, df):
        df['floatPenalty'] = df['penalty'].astype(float)

        df = df.sort_values('floatPenalty', ignore_index=True)

        return df.drop(columns='floatPenalty')

    pass


def updateSummaryInDf(row, item):
    if row['penalty'] == item['penalty']:
        return item
    return row
