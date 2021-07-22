from tests import Base
from pyramid import testing
from pyramid.paster import get_app
waitTime = 60


url = 'http://localhost:8080'


class PeakLearnerTests(Base.PeakLearnerTestBase):
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'

    def setUp(self):
        super().setUp()

        self.config = testing.setUp()
        app = get_app('production.ini')

        from webtest.http import StopableWSGIServer

        self.testapp = StopableWSGIServer.create(app, port=8080)

    def test_slurmRunner(self):

        from core.util import PLdb as db

        txn = db.getTxn()
        job = db.Job('2').get(txn=txn, write=True)

        job.problem['chromEnd'] = job.problem['chromStart'] + 1000

        db.Job('0').put(job, txn=txn)
        txn.commit()

        from Slurm.run import runTask

        while True:
            txn = db.getTxn()
            job = db.Job('2').get(txn=txn, write=True)
            txn.commit()

            # Empty dict default return for get when the job doesn't actually exist
            if isinstance(job, dict):
                break
            runTask()


    def tearDown(self):
        super().tearDown()

        self.testapp.close()
