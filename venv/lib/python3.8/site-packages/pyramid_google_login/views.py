import logging

from six.moves.urllib import parse
from pyramid.view import view_config
from pyramid.security import (remember, forget, NO_PERMISSION_REQUIRED)
from pyramid.httpexceptions import HTTPFound

from pyramid_google_login import redirect_to_signin, find_landing_path, SETTINGS_PREFIX
from pyramid_google_login.events import UserLoggedIn, UserLoggedOut
from pyramid_google_login.exceptions import AuthFailed

log = logging.getLogger(__name__)


def includeme(config):
    config.add_route('auth_signin', '/auth/signin')
    config.add_route('auth_signin_redirect', '/auth/signin_redirect')
    config.add_route('auth_callback', '/auth/oauth2callback')
    config.add_route('auth_logout', '/auth/logout')

    config.add_static_view('static/pyramid_google_login',
                           'pyramid_google_login:static',
                           cache_max_age=300)

    config.scan(__name__)


def encode_state(params):
    return parse.urlencode(params)


def decode_state(state):
    return parse.parse_qs(state)


@view_config(route_name='auth_signin',
             permission=NO_PERMISSION_REQUIRED,
             renderer='pyramid_google_login:templates/signin.mako')
def signin(request):
    googleapi_settings = request.registry.settings['googleapi_settings']
    message = request.params.get('message')
    url = request.params.get('url')

    if request.authenticated_userid:
        if url:
            return HTTPFound(location=url)
        else:
            return HTTPFound(location=find_landing_path(request))

    if url:
        redirect_url = request.route_url('auth_signin_redirect',
                                         _query={'url': url})
    else:
        redirect_url = request.route_url('auth_signin_redirect')

    return {'signin_redirect_url': redirect_url,
            'message': message,
            'signin_banner': googleapi_settings.signin_banner,
            'signin_advice': googleapi_settings.signin_advice,
            'hosted_domain': googleapi_settings.hosted_domain,
            }


@view_config(route_name='auth_signin_redirect',
             permission=NO_PERMISSION_REQUIRED,)
def signin_redirect(request):
    googleapi = request.googleapi
    settings = request.registry.settings
    app_url = settings.get(SETTINGS_PREFIX + 'app_url')
    if app_url is not None:
        redirect_uri = request.route_url('auth_callback', _app_url=app_url)
    else:
        redirect_uri = request.route_url('auth_callback')

    state_params = {}
    if 'url' in request.params:
        state_params['url'] = request.params['url']
    state = encode_state(state_params)

    try:
        authorize_url = googleapi.build_authorize_url(state, redirect_uri)
    except AuthFailed as err:
        log.warning('Google Login failed (%s)', err)
        return redirect_to_signin(request, 'Google Login failed (%s)' % err)

    return HTTPFound(location=authorize_url)


@view_config(route_name='auth_callback',
             permission=NO_PERMISSION_REQUIRED)
def callback(request):
    api = request.googleapi
    settings = request.registry.settings
    app_url = settings.get(SETTINGS_PREFIX + 'app_url')
    if app_url is not None:
        redirect_uri = request.route_url('auth_callback', _app_url=app_url)
    else:
        redirect_uri = request.route_url('auth_callback')
    try:
        oauth2_token = api.exchange_token_from_code(redirect_uri)
        userinfo = api.get_userinfo_from_token(oauth2_token)
        api.check_hosted_domain_user(userinfo)
        userid = api.get_user_id_from_userinfo(userinfo)

    except AuthFailed as err:
        log.warning('Google Login failed (%s)', err)
        return redirect_to_signin(request, 'Google Login failed (%s)' % err)

    except Exception as err:
        log.warning('Google Login failed (%s)', err)
        # Protect against leaking critical information like client_secret
        return redirect_to_signin(request, 'Google Login failed (unkown)')

    # Find the redirect url (fail-safe, the authentication is more important)
    try:
        state_params = decode_state(request.params['state'])
        url = state_params['url'][0]
    except Exception:
        url = find_landing_path(request)

    user_logged_in = UserLoggedIn(request, userid, oauth2_token, userinfo)
    try:
        request.registry.notify(user_logged_in)
    except Exception:
        log.exception('Application crashed processing UserLoggedIn event'
                      '\nuserinfo=%s oauth2_token=%s',
                      userinfo, oauth2_token)
        return redirect_to_signin(request,
                                  'Google Login failed (application error)')

    if user_logged_in.headers:
        headers = user_logged_in.headers
    else:
        headers = remember(request, userid)
    return HTTPFound(location=url, headers=headers)


@view_config(route_name='auth_logout')
def logout(request):
    userid = request.unauthenticated_userid
    if userid is not None:
        event = UserLoggedOut(userid)
        request.registry.notify(event)

    headers = forget(request)
    return redirect_to_signin(request, 'You are logged out!', headers=headers)
