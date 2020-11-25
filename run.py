import configparser
import threading
from api import httpServer, PLConfig as cfg, PLdb

httpArgs = (cfg.httpServerPort, cfg.jbrowsePath)

# start httpServer
server = threading.Thread(target=httpServer.httpserver, args=httpArgs)


def startServer():
    server.start()


def shutdown():
    httpServer.shutdownServer()
    server.join()
    PLdb.close()


if __name__ == '__main__':
    try:
        startServer()
    except KeyboardInterrupt:
        shutdown()
