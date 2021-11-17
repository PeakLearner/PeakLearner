import time

import core
import numpy as np
import pandas as pd
from core import models
from fastapi import Request, Depends
from sqlalchemy.orm import Session


def populateUserProfile(authUser, txn=None):
    hubsToShow = []
    allHubs = db.HubInfo.all_dict(txn)
    for key, hub in allHubs.items():
        user, hubName = key
        hub['hub'] = hubName
        if user == authUser:
            hubsToShow.append(hub)
        elif hub['isPublic']:
            hubsToShow.append(hub)
        else:
            perms = db.Permission(*key).get(txn=txn)

            if perms.hasPermission(authUser, 'Label'):
                hubsToShow.append(hub)

    output = []

    for hub in hubsToShow:
        hubOutput = {'owner': hub['owner'],
                     'hub': hub['hub'],
                     'numTracks': len(hub['tracks']),
                     'totalLabels': 0,
                     'userLabels': 0}
        hubLabels = []

        labelKeys = db.Labels.keysWhichMatch(hub['owner'], hub['hub'])

        for key in labelKeys:
            hubLabels.append(db.Labels(*key).get(txn=txn))

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

    user = db.query(models.User).filter(models.User.name == authUser).first()

    if user is None and authUser == 'Public':
        user = models.User(name=authUser)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

