from sqlalchemy import Boolean, PickleType, Column, Float, ForeignKey, Integer, String, ForeignKeyConstraint, Time
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
    hubName = Column(String(255))
    genome = Column(Integer, ForeignKey('genomes.id'))
    public = Column(Boolean)
    tracks = relationship('Track', lazy='dynamic')


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
    trackName = Column(String(255))
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
    problem = Column(Integer, ForeignKey('problems.id'))
    modelSums = relationship('ModelSum', lazy='dynamic')


class Label(Base):
    __tablename__ = 'labels'
    id = Column(Integer, primary_key=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))

    annotation = Column(String(10))
    start = Column(Integer)
    end = Column(Integer)
    lastModified = Column(Time)
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




