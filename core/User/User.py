import time

import core
import numpy as np
import pandas as pd
from core import models
from fastapi import Request, Depends
from sqlalchemy.orm import Session


def populateUserProfile(db, authUser):
    hubsToShow = []
    hubs = db.query(models.Hub).all()
    for hub in hubs:
        if hub.checkPermission(authUser, 'label'):
            hubsToShow.append(hub)

    output = []

    for hub in hubsToShow:
        owner = db.query(models.User).get(hub.owner)
        hubOutput = {'owner': owner.name,
                     'hub': hub.name,
                     'numTracks': len(hub.tracks.all()),
                     'totalLabels': 0,
                     'userLabels': 0}
        hubLabels = hub.getAllLabels(db)

        if len(hubLabels) > 0:
            allLabels = pd.concat(hubLabels)

            hubOutput['totalLabels'] = len(allLabels.index)
            try:
                userLabels = allLabels['lastModifiedBy'] == authUser
            except KeyError:
                pass

            try:
                hubOutput['userLabels'] = userLabels.value_counts()[True]
            except KeyError:
                pass

        output.append(hubOutput.copy())

    return output


def getAuthUser(request: Request, db: Session = Depends(core.get_db)):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    return getUser(authUser, db)


def getUser(userName, db: Session = Depends(core.get_db)):
    user = db.query(models.User).filter(models.User.name == userName).first()

    if user is None:
        user = models.User(name=userName)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

