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
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'

    async def setUp(self):
        """ Bring server up. """
        await super().setUp()

        import core.main as main

        self.proc = Process(target=uvicorn.run,
                            args=(main.app,),
                            kwargs={
                                "host": host,
                                "port": port,
                                "log_level": "info"},
                            daemon=True)
        self.proc.start()
        await asyncio.sleep(1)

    async def test_slurmRunner(self):

        from core.util import PLdb as db

        txn = db.getTxn()
        job = db.Job('2').get(txn=txn, write=True)

        job.problem['chromEnd'] = job.problem['chromStart'] + 1000

        db.Job('0').put(job, txn=txn)
        txn.commit()


        count = 0

        while True:
            # To prevent getting stuck here
            assert count < 50
            count += 1
            txn = db.getTxn()
            job = db.Job('2').get(txn=txn)
            txn.commit()

            # Empty dict default return for get when the job doesn't actually exist
            if isinstance(job, dict):
                break
            assert Slurm.run.runTask()

    async def tearDown(self):
        """ Shutdown the app. """
        super().tearDown()

        self.proc.terminate()
