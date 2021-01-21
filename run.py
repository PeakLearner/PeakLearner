import threading
import signal
from api.util import PLdb
import PeakLearnerWsgi
import api.Prediction.PeakSegDiskPredict as psgPred

# start httpServer
server = threading.Thread(target=PeakLearnerWsgi.startServer)
learning = threading.Thread(target=psgPred.runLearning)


def startServer():
    learning.start()
    server.start()
    signal.pause()


def shutdown():
    PeakLearnerWsgi.shutdownServer()
    psgPred.shutdown()
    server.join()
    PLdb.close()


if __name__ == '__main__':
    try:
        startServer()
    except (KeyboardInterrupt, SystemExit):
        shutdown()
