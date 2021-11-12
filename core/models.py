import pandas as pd
from sqlalchemy import Boolean, PickleType, Column, Float, ForeignKey, DateTime, Integer, String, ForeignKeyConstraint, Time
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    hubs = relationship('Hub', lazy='dynamic')
    labels = relationship('Label', lazy='dynamic')


class Hub(Base):
    __tablename__ = 'hubs'
    id = Column(Integer, primary_key=True)
    owner = Column(Integer, ForeignKey('users.id'))
    name = Column(String(255))
    genome = Column(Integer, ForeignKey('genomes.id'))
    public = Column(Boolean)
    tracks = relationship('Track', lazy='dynamic')
    permissions = relationship('HubPermission', lazy='dynamic')

    def checkPermission(self, user, permStr):
        perm = self.permissions.filter(HubPermission.user == user.id).first()

        if perm is None:
            return False
        return perm.checkPerm(permStr)


class HubPermission(Base):
    __tablename__ = 'hubperms'
    id = Column(Integer, primary_key=True)
    hubId = Column(Integer, ForeignKey('hubs.id'))
    user = Column(Integer, ForeignKey('users.id'))
    label = Column(Boolean)
    track = Column(Boolean)
    hub = Column(Boolean)
    moderator = Column(Boolean)

    permsDict = {'label': label,
                  'track': track,
                  'hub': hub,
                  'moderator': moderator}

    def checkPerm(self, permStr):
        return self.permsDict[permStr.lower()]


class Genome(Base):
    __tablename__ = 'genomes'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    problems = relationship('Problem', lazy='dynamic')
    hubs = relationship('Hub', lazy='dynamic')


class Problem(Base):
    __tablename__ = 'problems'
    id = Column(Integer, primary_key=True)
    genome = Column(Integer, ForeignKey('genomes.id'))
    chrom = Column(String(45))
    start = Column(Integer)
    end = Column(Integer)
    contigs = relationship('Contig', lazy='dynamic')


class Track(Base):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True)
    hub = Column(Integer, ForeignKey('hubs.id'))
    name = Column(String(255))
    categories = Column(String(255))
    url = Column(String(255))
    chroms = relationship('Chrom', lazy='dynamic')

    def getLabels(self, queryFilter=None, **kwargs):
        chromLabels = []
        chroms = self.chroms.all()

        for chrom in chroms:
            chromOut = chrom.getLabels(queryFilter=queryFilter[1:], **kwargs)
            if chromOut is not None:
                chromLabels.append(chromOut)

        if chromLabels:
            if queryFilter:
                return queryFilter[0](pd.concat(chromLabels), **kwargs)
            return pd.concat(chromLabels)


class Chrom(Base):
    __tablename__ = 'chroms'
    id = Column(Integer, primary_key=True)
    track = Column(Integer, ForeignKey('tracks.id'))
    name = Column(String(45))
    labels = relationship('Label', lazy='dynamic')
    contigs = relationship('Contig', lazy='dynamic')

    def getLabels(self, queryFilter=None, **kwargs):
        # Get all labels as list of dicts to turn into a df
        labels = self.labels.all()
        labelsOut = []

        for label in labels:
            labelDict = label.__dict__.copy()
            if 'id' in labelDict:
                del labelDict['id']
            labelDict['chrom'] = self.name
            labelsOut.append(labelDict)

        if labelsOut:
            if queryFilter:
                if isinstance(queryFilter, list):
                    return queryFilter[0](labelsOut, **kwargs)
                return queryFilter(labelsOut, **kwargs)
            else:
                return labelsOut


class Contig(Base):
    __tablename__ = 'contigs'
    id = Column(Integer, primary_key=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))
    features = Column(PickleType)
    problem = Column(Integer, ForeignKey('problems.id'))
    modelSums = relationship('ModelSum', lazy='dynamic')


class Label(Base):
    __tablename__ = 'labels'
    id = Column(Integer, primary_key=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))

    annotation = Column(String(10))
    start = Column(Integer)
    end = Column(Integer)
    lastModified = Column(DateTime)
    lastModifiedBy = Column(Integer, ForeignKey('users.id'))
    __dict__ = {'annotation': annotation,
                'start': start,
                'end': end,
                'lastModified': lastModified,
                'lastModifiedBy': lastModifiedBy}


class ModelSum(Base):
    __tablename__ = 'modelsums'
    id = Column(Integer, primary_key=True)
    contig = Column(Integer, ForeignKey('contigs.id'))
    penalty = Column(Float)
    fp = Column(Integer)
    fn = Column(Integer)
    possible_fp = Column(Integer)
    possible_fn = Column(Integer)
    errors = Column(Integer)
    numPeaks = Column(Integer)
    regions = Column(Integer)
    loss = Column(PickleType)
