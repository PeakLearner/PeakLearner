import os

import Slurm
Slurm.SlurmConfig.testing()
import requests
from tests import Base
from multiprocessing import Process

import asyncio

import uvicorn
waitTime = 60


host = 'localhost'
port = 8080
url = 'http://%s:%s' % (host, port)


class PeakLearnerTests(Base.PeakLearnerAsyncTestBase):
    dbFile = os.path.join('data', 'test.db')
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'

    async def setUp(self):
        """ Bring server up. """
        await super().setUp()

        self.proc = Process(target=uvicorn.run,
                            args=(self.app,),
                            kwargs={
                                "host": host,
                                "port": port,
                                "log_level": "info"},
                            daemon=True)
        self.proc.start()
        await asyncio.sleep(1)

    async def test_FeatureJob(self):
        # Runs a job
        assert Slurm.run.runTask()

    async def test_ModelJob(self):
        jobsUrl = os.path.join(url, 'Jobs', '11', '12')

        r = requests.get(jobsUrl)

        assert r.status_code == 200

        task = r.json()

        assert Slurm.Tasks.runTask(task)

    async def tearDown(self):
        """ Shutdown the app. """
        super().tearDown()

        self.proc.terminate()
