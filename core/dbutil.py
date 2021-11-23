from . import models
from sqlalchemy.orm import Session
from fastapi import Response


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


def getChrom(db: Session, user, hub, track, chrom: str, make=False):
    if isinstance(track, str):
        user, hub, track = getTrack(db, user, hub, track)

    if track is not None:
        chromFromDb = track.chroms.filter(models.Chrom.name == chrom).first()

        if chromFromDb is None:
            if make:
                chrom = models.Chrom(track=track.id, name=chrom)
                db.add(chrom)
                db.flush()
                db.refresh(chrom)

                return user, hub, track, chrom
        return user, hub, track, chromFromDb
    return None


def getChromAndCheckPerm(db: Session, authUser, user, hub, track, chrom, perm, make=False):
    if isinstance(hub, str):
        user, hub = getHub(db, user, hub)

    if not hub.checkPermission(authUser, perm):
        if authUser.name == 'Public':
            return Response(status_code=401)
        return Response(status_code=403)

    return getChrom(db, user, hub, track, chrom, make=make)


def getContig(db: Session, user, hub, track, chrom, start: int, make=False):
    if isinstance(chrom, str):
        user, hub, track, chrom = getChrom(db, user, hub, track, chrom, make=make)

    if chrom is not None:
        problem = hub.getProblems(db, chrom.name, start)

        problemId = problem.id.item()

        contig = chrom.contigs.filter(models.Contig.problem == problemId).first()

        if contig is None:
            if make:
                contig = models.Contig(chrom=chrom.id, problem=problemId)
                db.add(contig)
                db.flush()
                db.refresh(contig)

                return user, hub, track, chrom, contig, problem
        return user, hub, track, chrom, contig, problem
    return None
