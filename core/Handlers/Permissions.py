import simpleBDB
from core.util import PLdb as db
from core.Handlers.Handler import Handler


defaultPerms = {'Label': True, 'Track': False, 'Hub': False, 'Moderator': False}


class PermissionHandler(Handler):
    """Handles Job Commands"""

    def do_POST(self, data, txn=None):
        funcToRun = self.getCommands()[data['command']]
        args = {}
        if 'args' in data:
            args = data['args']

        return funcToRun(args, txn=txn)

    @classmethod
    def getCommands(cls):
        return {}


class Permission:

    def __init__(self, user, hub):
        self.owner = str(user)
        self.hub = hub
        self.users = {'Public': {'Label': True, 'Track': False, 'Hub': False, 'Moderator': False}}
        self.groups = {}

    @classmethod
    def fromStorable(cls, storable):
        """Create a permissions object from a storable object

        These storables are dicts which are stored using the Job type in api.util.PLdb
        """

        # https://stackoverflow.com/questions/2168964/how-to-create-a-class-instance-without-calling-initializer
        self = cls.__new__(cls)
        self.owner = str(storable['owner'])
        self.hub = storable['hub']
        self.users = storable['users']
        self.groups = storable['groups']
        return self

    def putNewPermissions(self):
        txn = db.getTxn()
        self.putPermissionsWithTxn(txn=txn)
        txn.commit()

    def putPermissionsWithTxn(self, txn=None):
        db.Permission(self.owner, self.hub).put(self.__dict__(), txn=txn)

    def hasViewPermission(self, userToCheck, hubInfo):
        if hubInfo['isPublic']:
            return True

        if 'Public' != userToCheck in self.users:
            return True

        if self.owner == userToCheck:
            return True

        # TODO: Add a way to check if a user is in a group which has permission

        return False

    def hasPermission(self, userToCheck, perm):
        if self.owner == userToCheck:
            return True

        if userToCheck is not None and userToCheck in self.users.keys():
            userKey = userToCheck
        else:
            userKey = 'Public'

        currentPerms = self.users[userKey]

        if currentPerms['Moderator']:
            return True

        return currentPerms[perm]

    def adjustPermissions(self, owner, hub, userid, coUser, args, txn=None):

        if not self.hasPermission(userid, 'Moderator'):
            raise simpleBDB.AbortTXNException

        if coUser in self.users:
            userPerms = self.users[coUser]

            for perm in userPerms.keys():
                if perm in args:
                    userPerms[perm] = True
                else:
                    userPerms[perm] = False

    def __dict__(self):
        output = {
            'owner': self.owner,
            'hub': self.hub,
            'users': self.users,
            'groups': self.groups
        }

        return output


@simpleBDB.retry
@simpleBDB.txnAbortOnError
def adjustPermissions(owner, hub, userid, coUser, args, txn=None):
    # create authorization
    permDb = db.Permission(owner, hub)
    perms = permDb.get(txn=txn, write=True)
    perms.adjustPermissions(owner, hub, userid, coUser, args, txn=txn)
    permDb.put(perms, txn=txn)
