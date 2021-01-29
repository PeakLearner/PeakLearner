import pandas as pd
from api.util import PLConfig as cfg, PLdb as db
import time

shutdownServer = False
changes = 0


def runLearning():
    lastRun = time.time()
    firstStart = True

    timeDiff = lambda: time.time() - lastRun

    try:
        while not shutdownServer:
            if timeDiff() > cfg.timeBetween or firstStart:
                firstStart = False
                print('starting Learning')
                learn()
                lastRun = time.time()
            else:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print('test')
    print('Learning loop stopped')


def learn():
    print()

    # if # Enough labeled regions

    #    if changes > cfg.numChanges:


    # if conditions to learn, start learning


def change(data):
    global changes
    changes = changes + 1


def shutdown():
    global shutdownServer
    shutdownServer = True


def problemToFeatureVec(coverage):
    print(coverage)

runLearning()