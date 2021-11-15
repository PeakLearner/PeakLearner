import datetime
import time

import numpy as np
import pandas as pd

from core.util import PLdb as pldb
from core.Models.Models import calculateModelLabelError
from core import database, models

pldb.openEnv()
pldb.openDBs()

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
            SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

database.Base.metadata.create_all(bind=engine)

with SessionLocal() as session:
    session.begin()

    if True:
        print('Migrating HubInfos')
        for key, hub in pldb.HubInfo.all_dict().items():
            tracks = hub['tracks']
            del hub['tracks']

            ownerName, hubName = key

            owner = session.query(models.User).filter(models.User.name == ownerName).first()

            if owner is None:
                owner = models.User(name=ownerName)
                session.add(owner)
                session.commit()
                session.refresh(owner)

            genome = session.query(models.Genome).filter(models.Genome.name == hub['genome']).first()
            if genome is None:
                genome = models.Genome(name=hub['genome'])
                session.add(genome)
                session.commit()
                session.refresh(genome)

            problems = pldb.Problems(hub['genome']).get()

            def putProblems(row):
                problem = genome.problems.filter(models.Problem.chrom == row['chrom'])\
                    .filter(models.Problem.start == row['chromStart']).first()
                if problem is None:
                    problem = models.Problem(genome=genome.id,
                                                  chrom=row['chrom'],
                                                  start=row['chromStart'],
                                                  end=row['chromEnd'])
                    session.add(problem)
                    session.commit()
                    session.refresh(problem)

            problems.apply(putProblems, axis=1)

            hubToInsert = owner.hubs.filter(models.Hub.name == hubName).first()
            if hubToInsert is None:
                hubToInsert = models.Hub(owner=owner.id, name=hubName, genome=genome.id, public=hub['isPublic'])
                session.add(hubToInsert)
                session.commit()
                session.refresh(hubToInsert)

            for trackKey, track in tracks.items():
                trackToInsert = hubToInsert.tracks.filter(models.Track.name == track['key']).first()
                if trackToInsert is None:
                    trackToInsert = models.Track(
                        hub=hubToInsert.id,
                        categories=track['categories'],
                        name=track['key'],
                        url=track['url'])

                    session.add(trackToInsert)

                    session.commit()
        print('Finished migrating HubInfos')

    print('---------------------------')

    if True:
        print('Migrating permissions')
        for key, permissions in pldb.Permission.all_dict().items():
            owner, hubName = key
            if owner == 'All' and hubName == 'Admin':
                continue

            owner = session.query(models.User).filter(models.User.name == ownerName).first()

            if owner is None:
                raise Exception

            hub = owner.hubs.filter(models.Hub.name == hubName).first()

            asDict = permissions.__dict__()

            for userName, perms in asDict['users'].items():

                user = session.query(models.User).filter(models.User.name == userName).first()

                if user is None:
                    user = models.User(name=userName)
                    session.add(user)
                    session.commit()
                    session.refresh(user)

                permissions = hub.permissions.filter(models.HubPermission.user == user.id).first()

                if permissions is None:
                    permissions = models.HubPermission(hubId=hub.id,
                                                       user=user.id,
                                                       label=perms['Label'],
                                                       track=perms['Track'],
                                                       hub=perms['Hub'],
                                                       moderator=perms['Moderator'])

                    session.add(permissions)
                    session.commit()
                    session.refresh(permissions)
        print('Finished migrating permissions')

    print('---------------------------')

    if True:
        print('Migrating Labels')
        allLabels = pldb.Labels.all_dict()
        totalLabelDfs = len(allLabels.keys())
        current = 0
        for key, labelDf in allLabels.items():
            ownerName, hubName, trackName, chromname = key

            owner = session.query(models.User).filter(models.User.name == ownerName).first()

            if owner is None:
                raise Exception

            hub = owner.hubs.filter(models.Hub.name == hubName).first()
            track = hub.tracks.filter(models.Track.name == trackName).first()
            chrom = track.chroms.filter(models.Chrom.name == chromname).first()

            if chrom is None:
                chrom = models.Chrom(track=track.id, name=chromname)
                session.add(chrom)
                session.commit()
                session.refresh(chrom)


            def putLabels(row):
                asDict = row.to_dict()

                if 'createdBy' in asDict:
                    del asDict['createdBy']

                checkLabel = chrom.labels.filter(models.Label.start == asDict['chromStart']).first()

                if checkLabel is None:
                    lastModifiedBy = None
                    if 'lastModifiedBy' in asDict:
                        lmb = asDict['lastModifiedBy']

                        if not isinstance(lmb, str):
                            asDict['lastModifiedBy'] = 'Public'

                        lastModifiedBy = session.query(models.User).filter(
                            models.User.name == asDict['lastModifiedBy']).first()
                    else:
                        asDict['lastModifiedBy'] = 'Public'
                        lastModifiedBy = session.query(models.User).filter(
                            models.User.name == 'Public').first()

                    if 'lastModified' in asDict:
                        lm = asDict['lastModified']
                        if lm is None or np.nan:
                            asDict['lastModified'] = datetime.datetime.now()

                    else:
                        asDict['lastModified'] = datetime.datetime.now()

                    if lastModifiedBy is None:
                        lastModifiedBy = models.User(name=asDict['lastModifiedBy'])
                        session.add(lastModifiedBy)
                        session.commit()
                        session.refresh(lastModifiedBy)

                    label = models.Label(chrom=chrom.id,
                                         start=asDict['chromStart'],
                                         end=asDict['chromEnd'],
                                         annotation=asDict['annotation'],
                                         lastModified=asDict['lastModified'],
                                         lastModifiedBy=lastModifiedBy.id)

                    session.add(label)
                    session.commit()

            labelDf.apply(putLabels, axis=1)
            current += 1
            print('Num labels to add left', totalLabelDfs - current)
        print('finished migrating labels')

    print('---------------------------')

    if True:
        print('Migrating Models')
        modelKeys = pldb.Model.db_key_tuples()
        numModels = len(modelKeys)
        current = 0

        for key in modelKeys:
            print('Num models to add left', numModels - current)
            current += 1
            ownerName, hubName, trackName, chromName, start, penalty = key
            owner = session.query(models.User).filter(models.User.name == ownerName).first()
            if owner is None:
                raise Exception
            hub = owner.hubs.filter(models.Hub.name == hubName).first()
            if hub is None:
                raise Exception
            genome = session.query(models.Genome).get(hub.genome)
            if genome is None:
                raise Exception
            track = hub.tracks.filter(models.Track.trackName == trackName).first()
            if track is None:
                raise Exception
            chrom = track.chroms.filter(models.Chrom.name == chromName).first()
            if chrom is None:
                chrom = models.Chrom(track=track.id, name=chromName)
                session.add(chrom)
                session.commit()
                session.refresh(chrom)
            labels = chrom.labels.all()
            if labels is None:
                raise Exception
            contigStartInt = int(start)

            problem = genome.problems.filter(models.Problem.chrom == chrom.name) \
                .filter(models.Problem.start == contigStartInt).first()
            if problem is None:
                raise Exception

            contig = chrom.contigs.filter(models.Contig.start == int(contigStartInt)).first()
            if contig is None:
                contig = models.Contig(chrom=chrom.id, start=contigStartInt, problem=problem.id)
                session.add(contig)
                session.commit()
                session.refresh(contig)

            floatPenalty = float(penalty)

            if floatPenalty == 0:
                continue

            modelSum = contig.modelSums.filter(models.ModelSum.penalty == floatPenalty).first()
            if modelSum is not None:
                continue

            modelDf = pldb.Model(*key).get()

            if len(modelDf.index) < 1:
                continue

            if len(labels) < 1:
                labelsDf = pd.DataFrame()
            else:
                labels = [{'chrom': problem.chrom,
                           'chromStart': label.start,
                           'chromEnd': label.end,
                           'annotation': label.annotation} for label in labels]

                labelsDf = pd.DataFrame(labels)

                isInBounds = labelsDf.apply(pldb.checkInBounds, axis=1, args=(problem.chrom, problem.start, problem.end))

                labelsDf = labelsDf[isInBounds]

            problemDict = {'chrom': problem.chrom,
                           'chromStart': problem.start, 'chromEnd': problem.end}
            modelSumOut = calculateModelLabelError(modelDf, labelsDf, problemDict, floatPenalty)

            loss = pldb.Loss(*key).get()

            if loss is None:
                modelSum = models.ModelSum(contig=contig.id,
                                           fp=modelSumOut['fp'],
                                           fn=modelSumOut['fn'],
                                           possible_fp=modelSumOut['possible_fp'],
                                           possible_fn=modelSumOut['possible_fn'],
                                           errors=modelSumOut['errors'],
                                           regions=modelSumOut['regions'],
                                           numPeaks=modelSumOut['numPeaks'],
                                           penalty=floatPenalty)
            else:
                modelSum = models.ModelSum(contig=contig.id,
                                           fp=modelSumOut['fp'],
                                           fn=modelSumOut['fn'],
                                           possible_fp=modelSumOut['possible_fp'],
                                           possible_fn=modelSumOut['possible_fn'],
                                           errors=modelSumOut['errors'],
                                           regions=modelSumOut['regions'],
                                           numPeaks=modelSumOut['numPeaks'],
                                           penalty=floatPenalty,
                                           loss=loss)

            session.add(modelSum)
            session.commit()
            session.refresh(modelSum)

            # TODO: Models out to fs

        print('finished migrating models')

    print('---------------------------')

    if True:
        print('Migrating Features')
        featureKeys = pldb.Features.db_key_tuples()
        numFeatures = len(featureKeys)
        current = 0

        for key in featureKeys:
            ownerName, hubName, trackName, chromName, start = key
            print('Num features to add left', numFeatures - current)
            current += 1
            owner = session.query(models.User).filter(models.User.name == ownerName).first()
            if owner is None:
                raise Exception
            hub = owner.hubs.filter(models.Hub.name == hubName).first()
            if hub is None:
                raise Exception
            genome = session.query(models.Genome).get(hub.genome)
            if genome is None:
                raise Exception
            track = hub.tracks.filter(models.Track.trackName == trackName).first()
            if track is None:
                raise Exception
            chrom = track.chroms.filter(models.Chrom.name == chromName).first()
            if chrom is None:
                chrom = models.Chrom(track=track.id, name=chromName)
                session.add(chrom)
                session.commit()
                session.refresh(chrom)
            contigStartInt = int(start)

            contig = chrom.contigs.filter(models.Contig.start == int(contigStartInt)).first()

            features = pldb.Features(*key).get()

            if contig is None:
                contig = models.Contig(chrom=chrom.id, start=contigStartInt, problem=problem.id, features=features)
                session.add(contig)
                session.commit()
                session.refresh(contig)
            else:
                contig.features = features
                session.commit()
                session.refresh(contig)
        print('finished migrating features')