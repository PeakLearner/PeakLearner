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


class HubPermission(Base):
    __tablename__ = 'hubperms'
    id = Column(Integer, primary_key=True)
    hubId = Column(Integer, ForeignKey('hubs.id'))
    user = Column(Integer, ForeignKey('users.id'))
    label = Column(Boolean)
    track = Column(Boolean)
    hub = Column(Boolean)
    moderator = Column(Boolean)


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


class Chrom(Base):
    __tablename__ = 'chroms'
    id = Column(Integer, primary_key=True)
    track = Column(Integer, ForeignKey('tracks.id'))
    name = Column(String(45))
    labels = relationship('Label', lazy='dynamic')
    contigs = relationship('Contig', lazy='dynamic')


class Contig(Base):
    __tablename__ = 'contigs'
    id = Column(Integer, primary_key=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))
    start = Column(Integer)
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
