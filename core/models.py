import pandas as pd
from sqlalchemy import Boolean, PickleType, Column, Float, ForeignKey, DateTime, Integer, String
from sqlalchemy.orm import relationship, Session
from core.util import bigWigUtil
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

    def getProblems(self, db: Session, ref=None, start: int = None, end: int = None):
        genome = db.query(Genome).filter(Genome.id == self.genome).first()
        problems = pd.read_sql(genome.problems.statement, db.bind)

        if ref is None:
            return problems
        elif isinstance(ref, str):
            refCheck = ref
        else:
            refCheck = ref.name
        chrom = problems[problems.chrom == refCheck]

        # Both start and end, get a range
        if start is not None is not end:
            inBounds = chrom.apply(bigWigUtil.checkInBounds, axis=1, args=(start, end))
            return chrom[inBounds]
        # Just start, try and get specific problem
        elif start is not None is end:
            output = chrom[chrom['start'] == start]

            if len(output.index) != 1:
                return None

            return output.iloc[0]
        else:
            return chrom


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

    def getLabels(self, db):
        # Get all labels as list of dicts to turn into a df
        labels = pd.read_sql(self.labels.statement, db.bind)
        labels['label_id'] = labels['id']
        labels['chrom'] = self.name
        return labels.set_index(['id'])


summaryColumns = ['regions', 'fp', 'possible_fp', 'fn', 'possible_fn', 'errors', 'numPeaks', 'penalty']


class Contig(Base):
    __tablename__ = 'contigs'
    id = Column(Integer, primary_key=True, index=True)
    chrom = Column(Integer, ForeignKey('chroms.id'))
    problem = Column(Integer, ForeignKey('problems.id'))
    features = Column(PickleType)
    iteration = Column(Integer, default=0)
    modelSums = relationship('ModelSum', lazy='dynamic')
    jobs = relationship('Job', lazy='dynamic')

    def getModelSums(self, db, withLoss=False):
        # Get all labels as list of dicts to turn into a df
        sums = pd.read_sql(self.modelSums.statement, db.bind).set_index(['id'])

        if withLoss:
            return sums

        return sums.drop('loss', axis=1)


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
    # PickleType because for some reason it was casting String(50) to float??
    penalty = Column(PickleType)
    fp = Column(Integer)
    fn = Column(Integer)
    possible_fp = Column(Integer)
    possible_fn = Column(Integer)
    errors = Column(Integer)
    numPeaks = Column(Integer)
    regions = Column(Integer)
    loss = Column(PickleType)


statuses = ['New', 'Queued', 'Processing', 'Done', 'Error', 'NoData']


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True, index=True)
    contig = Column(Integer, ForeignKey('contigs.id'))
    tasks = relationship('Task', lazy='dynamic')

    def getStatus(self):
        minIndex = len(statuses)
        tasks = self.tasks.all()

        for task in tasks:
            index = statuses.index(task.status)

            if index < minIndex:
                minIndex = index

        return statuses[minIndex]


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    taskType = Column(String(20))
    penalty = Column(PickleType)
    status = Column(String(20), default='New')
    job = Column(Integer, ForeignKey('jobs.id'))

    def addJobInfo(self, db):
        job = db.query(Job).get(self.job)
        contig = db.query(Contig).get(job.contig)
        problem = db.query(Problem).get(contig.problem)
        problem = {'chrom': problem.chrom, 'start': problem.start, 'end': problem.end}
        chrom = db.query(Chrom).get(contig.chrom)
        track = db.query(Track).get(chrom.track)
        hub = db.query(Hub).get(track.hub)
        user = db.query(User).get(hub.owner)
        return {'user': user.name,
                  'hub': hub.name,
                  'track': track.name,
                  'id': job.id,
                  'problem': problem,
                  'url': track.url,
                  'status': job.getStatus(),
                  'task': {
                      'id': self.id,
                      'taskType': self.taskType,
                      'penalty': self.penalty,
                      'status': self.status}}
