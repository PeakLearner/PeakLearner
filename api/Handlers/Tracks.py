from api.Handlers import Handler, Hubs
from api.util import PLdb as db, PLConfig as cfg
import pandas as pd
import os

problemColumns = ['chrom', 'chromStart', 'chromEnd']


class TrackInfoHandler(Handler.TrackHandler):
    """Handles Label Commands"""
    key = 'info'

    def do_GET(self, data):
        return getTrackInfo(data['args'])

    def do_POST(self, data):
        try:
            return self.getCommands()[data['command']](data['args'])
        except KeyError:
            print(data['command'], 'not yet implemented\n', data)

    @classmethod
    def getCommands(cls):
        return {'getGenome': getGenome,
                'getProblems': getProblems}


def getProblems(data):
    if 'genome' not in data:
        data['genome'] = getGenome(data)

    problems = db.Problems(data['genome'])

    problemsInBounds = problems.getInBounds(data['ref'], data['start'], data['end'])

    if problemsInBounds is None:
        problemsPath = os.path.join(cfg.jbrowsePath, cfg.dataPath, 'genomes', data['genome'], 'problems.bed')

        if not os.path.exists(problemsPath):
            location = Hubs.generateProblems(data['genome'], problemsPath)
            if not location == problemsPath:
                raise Exception

        problemsDf = pd.read_csv(problemsPath, sep='\t', header=None)
        problemsDf.columns = problemColumns
        problems.put(problemsDf)

        problemsIsInBounds = problemsDf.apply(db.checkInBounds, axis=1, args=(data['ref'], data['start'], data['end']))

        return problemsDf[problemsIsInBounds].to_dict('records')
    else:
        return problemsInBounds.to_dict('records')


def getGenome(data):
    hubInfo = db.HubInfo(data['user'], data['hub']).get()

    return hubInfo['genome']


def getTrackInfo(data):
    hubInfo = db.HubInfo(data['user'], data['hub']).get()

    return hubInfo['tracks'][data['track']]
