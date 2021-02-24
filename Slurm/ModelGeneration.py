import bbi
import os
import sys
import time
import numpy as np
import pandas as pd
import PeakSegDisk
import requests
import threading

try:
    import server.SlurmConfig as cfg
except ModuleNotFoundError:
    import SlurmConfig as cfg

genFeaturesPath = os.path.join('server', 'GenerateFeatures.R')


def generateModels(job, dataPath, coveragePath, trackUrl):
    data = job['jobData']
    penalties = data['penalties']

    modelThreads = []

    for penalty in penalties:
        modelData = job.copy()
        modelData['penalty'] = penalty

        modelArgs = (dataPath, modelData, trackUrl)

        modelThread = threading.Thread(target=generateModel, args=modelArgs)
        modelThreads.append(modelThread)
        modelThread.start()

    for thread in modelThreads:
        thread.join()


def gridSearch(job, dataPath, coveragePath, trackUrl):
    data = job['jobData']
    minPenalty = data['minPenalty']
    maxPenalty = data['maxPenalty']
    numModels = job['numModels']
    # Remove start and end of list because that is minPenalty/maxPenalty (already calculated)
    # Add 2 to numModels to account for start/end points (already calculated models)
    data['penalties'] = np.linspace(minPenalty, maxPenalty, numModels + 2).tolist()[1:-1]

    generateModels(job, dataPath, coveragePath, trackUrl)


# Helper Functions