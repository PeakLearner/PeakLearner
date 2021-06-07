from collections import namedtuple
import logging

from six.moves.urllib import parse
from pyramid.settings import aslist
from requests.exceptions import RequestException
import requests

from pyramid_google_login import SETTINGS_PREFIX
from pyramid_google_login.exceptions import AuthFailed, ApiError

from zope.interface import Interface

log = logging.getLogger(__name__)

ApiSettings = namedtuple(
    'ApiSettings',
    """
        access_type
        hosted_domain
        id
        landing_route
        landing_url
        scope_list
        secret
        signin_advice
        signin_banner
        user_id_field
        app_url
    """
    )


class IApiClientFactory(Interface):
    pass


class ApiClient(object):
    """-> https://developers.google.com/accounts/docs/OAuth2WebServer"""
    authorize_endpoint = 'https://accounts.google.com/o/oauth2/auth'
    token_endpoint = 'https://www.googleapis.com/oauth2/v3/token'
    userinfo_endpoint = 'https://www.googleapis.com/oauth2/v2/userinfo'
    domain_users_endpoint = ('https://www.googleapis.com'
                             '/admin/directory/v1/users')

    def __init__(self, request):
        self.request = request

        settings = self.request.registry.settings['googleapi_settings']
        self.id = settings.id
        self.secret = settings.secret
        self.hosted_domain = settings.hosted_domain
        self.access_type = settings.access_type
        self.scope_list = settings.scope_list
        self.user_id_field = settings.user_id_field

    def build_authorize_url(self, state, redirect_uri):
        params = {
            'response_type': 'code',
            'client_id': self.id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(self.scope_list),
            'state': state,
            'access_type': self.access_type,
        }

        if self.hosted_domain:
            params['hd'] = self.hosted_domain

        authorize_url = '%s?%s' % (
            self.authorize_endpoint,
            parse.urlencode(params)
        )

        return authorize_url

    def exchange_token_from_code(self, redirect_uri):
        if 'error' in self.request.params:
            raise AuthFailed(
                'Error from Google (%s)' % self.request.params['error'])
        try:
            code = self.request.params['code']
        except KeyError:
            raise AuthFailed('No authorization code from Google')

        params = {
            'code': code,
            'client_id': self.id,
            'client_secret': self.secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        try:
            response = requests.post(self.token_endpoint, data=params)
            response.raise_for_status()
            oauth2_tokens = response.json()

        except RequestException as err:
            raise AuthFailed('Failed to get token from Google (%s)' % err)

        except Exception:
            log.warning('Unkown error while calling token endpoint',
                        exc_info=True)
            raise AuthFailed('Failed to get token from Google (unkown error)')

        if 'access_token' not in oauth2_tokens:
            raise AuthFailed('No access_token in response from Google')

        return oauth2_tokens

    def get_userinfo_from_token(self, oauth2_tokens):
        try:
            params = {'access_token': oauth2_tokens['access_token']}
            response = requests.get(self.userinfo_endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            log.warning('Unkown error calling userinfo endpoint',
                        exc_info=True)
            raise AuthFailed('Failed to get userinfo from Google')

    def check_hosted_domain_user(self, userinfo):
        if not self.hosted_domain:
            return

        try:
            user_hosted_domain = userinfo['hd']
        except KeyError:
            raise AuthFailed('Missing hd field from Google userinfo')

        if self.hosted_domain != user_hosted_domain:
            raise AuthFailed('You logged in with an unkown domain '
                             '(%s rather than %s)' % (user_hosted_domain,
                                                      self.hosted_domain))

    def get_user_id_from_userinfo(self, userinfo):
        try:
            user_id = userinfo[self.user_id_field]
        except KeyError:
            raise AuthFailed('Missing user id field from Google userinfo')

        return user_id

    def refresh_access_token(self, refresh_token):
        params = {
            'client_id': self.id,
            'client_secret': self.secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }

        try:
            response = requests.post(self.token_endpoint, params=params)
            response.raise_for_status()
            oauth2_tokens = response.json()
        except RequestException as err:
            raise AuthFailed(err, 'Failed to get token from Google (%s)' % err)
        except Exception as err:
            log.warning('Unkown error while calling token endpoint',
                        exc_info=True)
            raise AuthFailed(err,
                             'Failed to get token from Google (unknown error)')

        if 'access_token' not in oauth2_tokens:
            raise AuthFailed('No access_token in response from Google')

        return oauth2_tokens

    def get_domain_users(self, access_token, limit=500):
        params = {
            'maxResults': limit,
            'domain': 'ludia.com',
            'viewType': 'domain_public',
            'access_token': access_token
        }
        try:
            response = requests.get(self.domain_users_endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except (ValueError, RequestException) as err:
            raise ApiError(err, 'Failed to get domain users (%s)' % err)


def includeme(config):
    settings = config.registry.settings
    prefix = SETTINGS_PREFIX

    scope_list = set(aslist(settings.get(prefix + 'scopes', '')))
    scope_list.add('email')
    try:
        api_settings = ApiSettings(
            access_type=settings.get(prefix + 'access_type', 'online'),
            hosted_domain=settings.get(prefix + 'hosted_domain'),
            id=settings[prefix + 'client_id'],
            landing_route=settings.get(prefix + 'landing_route'),
            landing_url=settings.get(prefix + 'landing_url'),
            scope_list=scope_list,
            secret=settings[prefix + 'client_secret'],
            signin_advice=settings.get(prefix + 'signin_advice'),
            signin_banner=settings.get(prefix + 'signin_banner'),
            user_id_field=settings.get(prefix + 'user_id_field', 'email'),
            app_url=settings[prefix + 'app_url']
            )
    except KeyError as err:
        log.error('Missing configuration setting: %s', err)
        raise

    config.add_settings(googleapi_settings=api_settings)

    config.registry.registerUtility(ApiClient, provided=IApiClientFactory)
    config.add_request_method(new_api_client, 'googleapi', reify=True)


def new_api_client(request):
    return request.registry.getUtility(IApiClientFactory)(request)
