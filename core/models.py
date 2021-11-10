from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, ForeignKeyConstraint
from sqlalchemy.orm import relationship


from .database import Base


class User(Base):
    __tablename__ = 'users'
    name = Column(String(255), primary_key=True)
    hubs = relationship('Hub', back_populates='owner')


class Hub(Base):
    __tablename__ = 'hubs'
    ownerName = Column(String(255), ForeignKey('users.name'), primary_key=True)
    hubName = Column(String(255), primary_key=True)
    genome = Column(String(45))
    public = Column(Boolean)

    owner = relationship('User', back_populates='hubs')
    tracks = relationship('Track', backref='hub')


class Track(Base):
    __tablename__ = 'tracks'

    trackName = Column(String(255), primary_key=True)
    ownerName = Column(String(255), primary_key=True)
    hubName = Column(String(255), primary_key=True)
    categories = Column(String(255))
    url = Column(String(255))

    __table_args__ = (ForeignKeyConstraint([ownerName, hubName],
                                           ['hubs.ownerName', 'hubs.hubName'], name='tracks'), {})