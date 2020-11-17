import configparser
import threading
from api import httpServer, PLConfig as cfg, PLdb

httpArgs = (cfg.httpServerPort, cfg.httpServerPath)

# start servers
httpServer = threading.Thread(target=httpServer.httpserver, args=httpArgs)


def startServer():
    httpServer.start()


def joinServer():
    httpServer.join()


try:
    startServer()
except KeyboardInterrupt:
    joinServer()
