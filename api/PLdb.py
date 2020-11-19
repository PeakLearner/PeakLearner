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


class Labels(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart")
    pass


class ModelSummaries(db.Container):
    keys = ("user", "hub", "track", "chrom", "problemstart")

    def make_details(self):
        newDf = pd.DataFrame()
        return newDf

    def add_item(self, df):
        if len(df.index) < 1:
            output = df.append(self.item, ignore_index=True)
        elif isinstance(self.item, pd.Series):
            exists = (self.item['penalty'] == df['penalty']).any()

            if exists:
                output = df.apply(updateSummaryInDf, axis=1, args=(self.item,))
            else:
                output = df.append(self.item, ignore_index=True)
        elif isinstance(self.item, pd.DataFrame):
            self.item['exists'] = self.item.apply(checkPenaltyExists, axis=1, args=(df,))

            exists = self.item[self.item['exists']]

            notExists = self.item[~self.item['exists']]

            updated = df.apply(updateExisting, axis=1, args=(exists,))

            output = updated.append(notExists, ignore_index=True).drop(columns='exists')
        else:
            output = df

        output['floatPenalty'] = output['penalty'].astype(float)

        output = output.sort_values('floatPenalty', ignore_index=True)

        return output.drop(columns='floatPenalty')

    def remove_item(self, df):
        return df[~(df['penalty'] == self.item['penalty'])]

    pass


def updateSummaryInDf(row, item):
    if row['penalty'] == item['penalty']:
        return item
    return row


def updateExisting(row, df):
    df['dupe'] = row['penalty'] == df['penalty']

    if df['dupe'].any():
        duped = df[df['dupe']]

        if not len(duped.index) == 1:
            print('multiple dupes', row, df)
            raise Exception

        output = duped.iloc[0].drop('dupe')
    else:
        output = row

    return output


def checkPenaltyExists(row, dfToCheck):
    duplicate = dfToCheck['penalty'] == row['penalty']
    return duplicate.any()
