from pyramid.security import Allow
import uuid

# DEFINE MEMBER MODEL
class User(object):
    @property
    def __acl__(self):
        return [
            (Allow, self.uid, 'view'),
        ]

    def __init__(self, token, groups=None):
        self.uid = uuid.uuid4()
        self.token = token
        self.groups = groups or []

    def check_token(self, token):
        return self.token == token

    def __str__(self):
        return "{self.uid}".format(self=self)