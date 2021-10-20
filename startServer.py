import os
import atexit
import uvicorn
import requests


from apscheduler.schedulers.background import BackgroundScheduler
# https://stackoverflow.com/questions/49269343/how-to-use-background-scheduler-with-an-flask-gunicorn-app
scheduler = BackgroundScheduler()

host = '0.0.0.0'
port = 8080
bind = '%s:%s' % (host, port)
url = 'http://%s' % bind
numWorkers = 4
waited = 0


# Kind of a hack using requests to make the tasks run inside a worker which has a database connection

# Background tasks
def spawnJobs():
    global waited
    if waited > 5:
        requests.get(os.path.join(url, 'runJobSpawn'))
    else:
        waited += 1


def checkJobsRestart():
    requests.get(os.path.join(url, 'checkRestartJobs'))


def runPrediction():
    requests.get(os.path.join(url, 'runPrediction'))


def doBackup():
    requests.get(os.path.join(url, 'backup'))


def startup():
    from core.util import PLdb as db
    db.clearLocks()


scheduler.add_job(doBackup, 'cron', hour=0)
scheduler.add_job(spawnJobs, 'interval', seconds=30)
scheduler.add_job(runPrediction, 'interval', minutes=10)
scheduler.add_job(checkJobsRestart, 'interval', minutes=60)


if __name__ == '__main__':
    startup()
    scheduler.start()
    uvicorn.run('core.main:app', host=host, port=port, workers=1)
