import os
import sys
import time
import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

try:
    import Tasks as tasks
    import SlurmConfig as cfg
except ModuleNotFoundError:
    import Slurm.Tasks as tasks
    import Slurm.SlurmConfig as cfg


def runTask():
    queueUrl = os.path.join(cfg.jobUrl, 'queue')
    try:
        r = requests.get(queueUrl, timeout=10, verify=cfg.verify)
    except requests.exceptions.ReadTimeout:
        print('timeout')
        return False

    if not r.status_code == 200:
        print(queueUrl)
        print('status', r.status_code)
        return False

    task = r.json()

    return tasks.runTask(task)


if __name__ == '__main__':
    if runTask():
        time.sleep(15)
