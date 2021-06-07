
class Event(object):
    pass


class UserLoggedIn(Event):
    def __init__(self, request, userid, oauth2_token, userinfo):
        self.request = request
        self.userid = userid
        self.oauth2_token = oauth2_token
        self.userinfo = userinfo
        self.headers = None


class UserLoggedOut(Event):
    def __init__(self, userid):
        self.userid = userid
