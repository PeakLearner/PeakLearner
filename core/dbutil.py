from . import models
from sqlalchemy.orm import Session


def getUser(db: Session, user: str):
    return db.query(models.User).filter(models.User.name == user).first()


def getHub(db: Session, user, hub: str):
    if isinstance(user, str):
        user = getUser(db, user)

    if user is not None:
        return user, user.hubs.filter(models.Hub.name == hub).first()
    return user, None


def getTrack(db: Session, user, hub, track: str):
    if isinstance(hub, str):
        user, hub = getHub(db, user, hub)

    if hub is not None:
        return user, hub, hub.tracks.filter(models.Track.name == track).first()
    return user, hub, None


def getChrom(db: Session, user, hub, track, chrom: str):
    if isinstance(track, str):
        user, hub, track = getTrack(db, user, hub, track)

    if track is not None:
        return user, hub, track, track.chroms.filter(models.Chrom.name == chrom).first()
    return None


