import os
import sys
import time
import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


import Tasks as tasks
import SlurmConfig as cfg


def runTask():
    queueUrl = '%squeue/' % cfg.jobUrl
    try:
        r = requests.get(queueUrl, timeout=10, verify=cfg.verify)
    except requests.exceptions.ReadTimeout:
        return False

    if not r.status_code == 200:
        return False

    task = r.json()

    return tasks.runTask(task)


if __name__ == '__main__':
    if runTask():
        time.sleep(15)
