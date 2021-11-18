""" This file's functions are left over from a refactor but they still work and I dont really know a better place to put them"""


import os
import pandas as pd
from core.Hubs import Hubs
from core.util import PLdb as db, PLConfig as cfg

problemColumns = ['chrom', 'chromStart', 'chromEnd']


def getProblemsForChrom(genome, chrom, txn=None):
    """Get the contigs for a problem given a chrom"""
    problems = db.Problems(genome).get(txn=txn)

    return problems[problems['chrom'] == chrom].copy()


def getProblems(db, data):
    """Get all the contigs given a given query"""
    if 'genome' not in data:
        data['genome'] = getGenome(db, data)

    problems = db.Problems(data['genome'])

    problemsInBounds = problems.getInBounds(data['ref'], data['start'], data['end'])

    if problemsInBounds is None:
        problemsPath = os.path.join(cfg.dataPath, 'genomes', data['genome'], 'problems.bed')

        if not os.path.exists(problemsPath):
            location = Hubs.generateProblems(db, data['genome'], problemsPath)
            if not location == problemsPath:
                raise Exception

        problemsDf = pd.read_csv(problemsPath, sep='\t', header=None)
        problemsDf.columns = problemColumns
        problems.put(problemsDf, txn=txn)

        problemsIsInBounds = problemsDf.apply(db.checkInBounds, axis=1, args=(data['ref'], data['start'], data['end']))

        return problemsDf[problemsIsInBounds].to_dict('records')
    else:
        return problemsInBounds.to_dict('records')


def getGenome(data, txn=None):
    """Get the genome for a hub"""
    hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)

    return hubInfo['genome']


def getTrackInfo(data, txn=None):
    """Returns info about a track in a hub"""
    hubInfo = db.HubInfo(data['user'], data['hub']).get(txn=txn)

    return hubInfo['tracks'][data['track']]
