import threading
from api.util import PLdb
import PeakLearnerWsgi

# start httpServer
server = threading.Thread(target=PeakLearnerWsgi.startServer)


def startServer():
    server.start()


def shutdown():
    PeakLearnerWsgi.shutdownServer()
    server.join()
    PLdb.close()


if __name__ == '__main__':
    try:
        startServer()
    except KeyboardInterrupt:
        shutdown()
