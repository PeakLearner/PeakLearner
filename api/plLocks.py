import threading


class layerLock:
    def __init__(self, name='init', parent=None):
        self.name = name
        self.lock = threading.Lock()
        self.children = {}
        self.parent = parent

    def acquire(self):
        self.lock.acquire()
        for child in self.children.values():
            child.acquire()

    def release(self):
        self.lock.release()
        for child in self.children.values():
            child.release()

    def getLock(self, layers):
        if len(layers) > 0:
            try:
                return self.children[layers[0]].getLock(layers[1:])
            except KeyError:
                output = layerLock(layers[0])
                self.children[layers[0]] = output
                return output.getLock(layers[1:])

        return self


topLock = layerLock()


def getLock(name):
    nameVals = name.split('/')
    topLock.lock.acquire()
    output = topLock.getLock(nameVals)
    topLock.lock.release()
    return output
