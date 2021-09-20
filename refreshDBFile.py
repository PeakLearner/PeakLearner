# needed for any cluster connection
import json
import pickle
import asyncio
import requests

import numpy

from core.util import PLdb as db, PLConfig as cfg


db.openDBs()


url = 'http://localhost:8080'


class RedisHandler:
    async def hubs(self):
        newHubDict = {}

        for key, permissions in db.Permission.all_dict().items():
            user, hub = key

            newHubDict[str(key)] = {'permissions': permissions.__dict__(), 'user': user, 'hub': hub}

        for key, hubInfo in db.HubInfo.all_dict().items():
            newHubDict[str(key)]['info'] = hubInfo

        requests.put(url + '/uploadHubDict', json=newHubDict)

    async def labels(self):
        allLabels = db.Labels.all_dict()

        for key, labels in allLabels.items():
            user, hub, track, chrom = key

            output = {'user': user,
                      'hub': hub,
                      'track': track,
                      'chrom': chrom,
                      'labels': labels.to_json()}

            requests.put(url + '/putLabelsRefresh', json=output)

    async def other(self):
        allProblems = db.Problems.all_dict()

        for key, contigs in allProblems.items():
            await r.set(key[0], contigs.to_json())

        await r.set('refseqs', json.dumps(list(allProblems.keys())))

    def toStorablePrediction(self, toStore):
        if isinstance(toStore, dict):
            newDict = {}

            for key in toStore.keys():
                newDict[key] = self.toStorablePrediction(toStore[key])

            return newDict

        elif isinstance(toStore, numpy.ndarray):
            return toStore.tolist()

        return toStore

    async def modelSumFeatures(self):
        startVals = {}

        for key, feature in db.Features.all_dict().items():
            startVals[str(key)] = {'features': feature.to_json()}

        for key, modelSum in db.ModelSummaries.all_dict().items():
            startVals[str(key)]['modelSum'] = modelSum.to_json()

        for key in startVals.keys():
            await r.set(key, json.dumps(startVals[key]))

        await r.set('modelSumFeatures', json.dumps(list(startVals.keys())))

    async def lossModels(self):
        lossAndModel = {}

        for key, loss in db.Loss.all_dict().items():
            user, hub, track, chrom, start, penalty = key
            lossAndModel[str(key)] = {'loss': loss.to_json(),
                                      'user': user,
                                      'hub': hub,
                                      'track': track,
                                      'chrom': chrom,
                                      'chromStart': start,
                                      'penalty': penalty}

        for key, model in db.Model.all_dict().items():
            lossAndModel[str(key)]['model'] = model.to_json()

        modelsSent = 0
        totalModels = len(lossAndModel.keys())

        pipe = await r.pipeline()
        for key in lossAndModel.keys():
            pipe.set(key, json.dumps(lossAndModel[key]))
            modelsSent += 1
            print('models Sent', modelsSent)
            print('models left', totalModels - modelsSent)

        pipe.set('models', json.dumps(list(lossAndModel.keys())))

        await pipe.execute()

    async def jobs(self):
        # Next Job Id
        currentJobId = db.JobInfo('Id').get()

        await r.set('currentJobId', currentJobId)

        # Job Iterations
        allIters = db.Iteration.all_dict()


        for key, iters in allIters.items():

            key = str(key)
            startVel = await r.get(key)

            if startVel is None:
                await r.set(key, iters)
                continue
            else:
                try:
                    test = int(startVel)
                except:

                    print(key, startVel)
                    break

        await r.set('iterations', json.dumps(list(allIters.keys())))

        currentJobs = db.Job.all_dict()

        # Jobs
        current = 0
        for key, job in currentJobs.items():
            print(key[0])
            await r.set(key[0], json.dumps(job.__dict__()))

        await r.set('Jobs', json.dumps(list(currentJobs)))

        doneJobs = db.DoneJob.all_dict()

        for key, job in doneJobs.items():
            print(key[0])
            await r.set(key[0], json.dumps(job.__dict__()))

        await r.set('DoneJobs', json.dumps(list(doneJobs)))

    async def predictions(self):
        predictionStuff = db.Prediction.all_dict()

        for key, val in predictionStuff.items():
            if key[0] == 'model':
                storable = pickle.dumps(val)

                await r.set(key[0], storable)

            else:
                await r.set(key[0], json.dumps(val))

    async def doTest(self):
        test = await r.keys('*')

        # print(test)
        print(len(test))


async def run():
    handler = RedisHandler()
    # await handler.hubs()
    # await handler.labels()
    await handler.other()
    # await handler.modelSumFeatures()
    # await handler.lossModels()
    # await handler.jobs()
    # await handler.predictions()
    # await handler.doTest()


if __name__ == '__main__':
    asyncio.run(run())




