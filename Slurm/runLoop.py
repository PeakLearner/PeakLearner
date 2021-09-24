import time
from multiprocessing import Process

try:
    import run as run
    import SlurmConfig as cfg
except ModuleNotFoundError:
    import Slurm.run as run
    import Slurm.SlurmConfig as cfg


def loop():
    while True:
        if not run.runTask():
            time.sleep(15)


if __name__ == '__main__':
    for num in range(cfg.numWorkers):
        Process(target=loop).start()
