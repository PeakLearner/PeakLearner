import pandas as pd
from sqlalchemy import Boolean, PickleType, Column, Float, ForeignKey, DateTime, Integer, String
from sqlalchemy.orm import relationship, Session

from .database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    hubs = relationship('Hub', lazy='dynamic')
    labels = relationship('Label', lazy='dynamic')


class Hub(Base):
    __tablename__ = 'hubs'
    id = Column(Integer, primary_key=True, index=True)
    owner = Column(Integer, ForeignKey('users.id'))
    name = Column(String(255))
    genome = Column(Integer, ForeignKey('genomes.id'))
    public = Column(Boolean)
    tracks = relationship('Track', lazy='dynamic')
    permissions = relationship('HubPermission', lazy='dynamic')

    def checkPermission(self, user, permStr):
        permStr = permStr.lower()

        # Everyone can label a public hub
        if permStr == 'label' and self.public:
            return True

        perm = self.permissions.filter(HubPermission.user == user.id).first()

        if perm is None:
            return False
        return perm.checkPerm(permStr)


class HubPermission(Base):
    __tablename__ = 'hubperms'
    id = Column(Integer, primary_key=True, index=True)
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
        return self.permsDict[permStr]


class Genome(Base):
    __tablename__ = 'genomes'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    problems = relationship('Problem', lazy='dynamic')
    hubs = relationship('Hub', lazy='dynamic')


class Problem(Base):
    __tablename__ = 'problems'
    id = Column(Integer, primary_key=True, index=True)
    genome = Column(Integer, ForeignKey('genomes.id'))
    chrom = Column(String(45))
    start = Column(Integer)
    end = Column(Integer)
    contigs = relationship('Contig', lazy='dynamic')


class Track(Base):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True, index=True)
    hub = Column(Integer, ForeignKey('hubs.id'))
    name = Column(String(255))
    categories = Column(String(255))
    url = Column(String(255))
    chroms = relationship('Chrom', lazy='dynamic')

    def getLabels(self, db):
        chromLabels = []
        chroms = self.chroms.all()

        for chrom in chroms:
            chromOut = chrom.getLabels(db)
            if chromOut is not None:
                chromLabels.append(chromOut)

        if chromLabels:
            return pd.concat(chromLabels)


class Chrom(Base):
    __tablename__ = 'chroms'
    id = Column(Integer, primary_key=True, index=True)
    track = Column(Integer, ForeignKey('tracks.id'))
    name = Column(String(45))
    labels = relationship('Label', lazy='dynamic')
    contigs = relationship('Contig', lazy='dynamic')

    def getLabels(self, db: Session):
        # Get all labels as list of dicts to turn into a df
        labels = pd.read_sql(self.labels.statement, db.bind)
        labels['label_id'] = labels['id']
        labels['chrom'] = self.name
        return labels.set_index(['id'])


class Contig(Base):
    __tablename__ = 'contigs'
    id = Column(Integer, primary_key=True, index=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))
    features = Column(PickleType)
    problem = Column(Integer, ForeignKey('problems.id'))
    modelSums = relationship('ModelSum', lazy='dynamic')


class Label(Base):
    __tablename__ = 'labels'
    id = Column(Integer, primary_key=True, unique=True, index=True)
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
    id = Column(Integer, primary_key=True, index=True)
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
