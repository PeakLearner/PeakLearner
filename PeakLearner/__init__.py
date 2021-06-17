import os
from pyramid.security import Allow
from website.users.Users import USERS
from pyramid.config import Configurator
from pyramid.security import ALL_PERMISSIONS
from pyramid.events import NewResponse, subscriber
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy


class RootFactory(object):
    """ replace default factory to give default permissions to users """

    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class UserFactory(object):
    """ routes accessing user object must use this factory """

    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        user = USERS[key]
        user.__parent__ = self
        user.__name__ = key
        return user


def group_finder(userid, request):
    """ returns groups of a given userid in USERS """

    user = USERS.get(userid)
    if user:
        return ['g:%s' % g for g in user.groups]


@subscriber(NewResponse)
def add_cors_headers(event):
    if event.request.is_xhr:
        event.response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
        })


def main(global_config, **settings):
    """Prepare a Pyramid app."""
    config = Configurator(settings=settings)

    # create authentication and authorization policies
    authn_policy = AuthTktAuthenticationPolicy(
        config.get_settings()['security.google_login.client_secret'],
        callback=group_finder,
    )
    authz_policy = ACLAuthorizationPolicy()

    # set config settings
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.set_root_factory(RootFactory)

    # Front end page
    config.add_route('home', '')
    config.add_route('about', '/about/')
    config.add_route('newHub', '/newHub/')
    config.add_route('tutorial', '/tutorial/')
    config.add_route('stats', '/stats/')
    config.add_route('modelStats', '/stats/model/')
    config.add_route('labelStats', '/stats/label/')
    config.add_static_view(name='assets', path='website:static/assets')
    config.add_route('public', '/public/{user}/{hub}/')
    config.add_route('myHubs', '/myHubs/')
    config.add_route('moreHubInfo', '/myHubs/{owner}/{hub}/moreInfo/')
    config.add_route('uploadHubUrl', '/uploadHubUrl/')
    config.add_route('jobInfo', '/jobs/info/')
    config.add_route('help', '/help/')
    config.add_route('login', '/login/')
    config.add_route('failed', '/failed/')
    config.add_route('authenticate', '/authenticate/')
    config.add_route('logout', '/logout/')


    # rendering related configurations
    config.include('pyramid_jinja2')
    config.include('pyramid_google_login')  # library for google oauth
    config.add_static_view(name='tutorial/static', path='website:static/tutorial')
    config.add_static_view(name='about', path='website:static/about')
    config.add_static_view(name='myHubs/static', path='website:static/')
    config.add_jinja2_renderer('.html')
    config.scan('website.views')

    config.include("pyramid_openapi3")
    config.add_static_view(name="spec", path="spec")
    config.pyramid_openapi3_spec_directory(os.path.join(os.path.dirname(__file__), "spec/openapi.yaml"))
    config.pyramid_openapi3_add_explorer()

    config.add_route('adjustPerms', '/{user}/{hub}/permissions/')
    config.add_route('addUser', '/{user}/{hub}/addUser/')
    config.add_route('removeUser', '/{user}/{hub}/removeUser/')
    config.scan('core.Permissions.views')

    config.add_route('jobs', '/Jobs/')
    config.add_route('jobQueue', '/Jobs/queue/')
    config.add_route('jobsWithId', '/Jobs/{jobId}/')
    config.add_route('resetJob', '/Jobs/{jobId}/reset/')
    config.add_route('restartJob', '/Jobs/{jobId}/restart/')
    config.scan('core.Jobs.views')

    config.add_route('hubInfo', '/{user}/{hub}/info/')

    config.add_route('hubLabels', '/{user}/{hub}/labels/')
    config.add_route('trackLabels', '/{user}/{hub}/{track}/labels/')
    config.scan('core.Labels.views')

    config.add_route('hubModels', '/{user}/{hub}/models/')
    config.add_route('trackModels', '/{user}/{hub}/{track}/models/')
    config.scan('core.Models.views')

    config.add_route('features', '/{user}/{hub}/{track}/features/')
    config.scan('core.Features.views')

    config.add_route('loss', '/{user}/{hub}/{track}/loss/')
    config.scan('core.Loss.views')

    config.add_route('addTrack', '/{user}/{hub}/addTrack/')
    config.add_route('removeTrack', '/{user}/{hub}/removeTrack/')
    config.add_route('deleteHub', '/{user}/{hub}/delete/')
    config.add_route('unlabeledHub', '/{user}/{hub}/unlabeled/')
    config.add_route('labeledHub', '/{user}/{hub}/labeled/')
    config.add_route('jbrowseJson', '/{user}/{hub}/data/{handler}')
    config.scan('core.Hubs.views')
    config.add_static_view(name='/{user}/{hub}', path='jbrowse:jbrowse')


    from wsgicors import CORS
    return CORS(config.make_wsgi_app(), headers="*", methods="*", maxage="180", origin="*")
