import mock
from pyramid.config import Configurator
from pyramid.decorator import reify
from requests.exceptions import RequestException

from . import Base


class TestIncludeme(Base):

    def test_includeme_missing_settings(self):
        config = Configurator(settings={})

        with self.assertRaises(KeyError):
            config.include('pyramid_google_login.utility')


class TestUtility(Base):

    @reify
    def googleapi(self):
        self.addCleanup(delattr, self, 'googleapi')
        return self.get_googleapi()

    def get_googleapi(self, path='/'):
        from pyramid_google_login.utility import ApiClient
        return ApiClient(self.get_request(path))


@mock.patch('pyramid_google_login.utility.requests.post')
class TestRefreshAccessToken(TestUtility):

    def test_nominal(self, post):
        response = post.return_value
        response.json.return_value = expected = {
            'access_token': 'i am a token',
        }
        self.assertEqual(
            expected,
            self.googleapi.refresh_access_token('refresh token'),
            )

    def test_raises_request_exception(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.raise_for_status.side_effect = RequestException('sh*t!')
        with self.assertRaises(AuthFailed):
            self.googleapi.refresh_access_token('refresh token')

    def test_raises_any_exception(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.json.side_effect = ValueError('cr*p!')
        with self.assertRaises(AuthFailed):
            self.googleapi.refresh_access_token('refresh token')

    def test_no_token_in_response(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.json.return_value = {
            'not_access_token': 'i am a NOT token',
        }
        with self.assertRaises(AuthFailed):
            self.googleapi.refresh_access_token('refresh token')


@mock.patch('pyramid_google_login.utility.requests.post')
class TestExchangeTokenFromCode(TestUtility):

    def test_nominal(self, post):
        response = post.return_value
        response.json.return_value = expected = {
            'access_token': 'i am a token',
        }

        googleapi = self.get_googleapi('/?code=CODE')
        self.assertEqual(
            expected,
            googleapi.exchange_token_from_code('http://redirect_uri.com')
            )

        endpoint = 'https://www.googleapis.com/oauth2/v3/token'
        params = {
            'code': 'CODE',
            'client_id': 'client id',
            'client_secret': 'client secret',
            'redirect_uri': 'http://redirect_uri.com',
            'grant_type': 'authorization_code',
        }

        post.assert_called_once_with(endpoint, data=params)

    def test_error_in_params(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        googleapi = self.get_googleapi('/?error=f*ck')
        with self.assertRaises(AuthFailed):
            googleapi.exchange_token_from_code('http://redirect_uri.com')

    def test_raises_request_exception(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.raise_for_status.side_effect = RequestException('cheis')

        googleapi = self.get_googleapi('/?code=CODE')
        with self.assertRaises(AuthFailed):
            googleapi.exchange_token_from_code('http://redirect_uri.com')

        self.assertTrue(post.called)

    def test_raises_any_exception(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.raise_for_status.side_effect = Exception('cheis')

        googleapi = self.get_googleapi('/?code=CODE')
        with self.assertRaises(AuthFailed):
            googleapi.exchange_token_from_code('http://redirect_uri.com')

        self.assertTrue(post.called)

    def test_no_token_in_response(self, post):
        from pyramid_google_login.exceptions import AuthFailed
        response = post.return_value
        response.json.return_value = {
            'not_access_token': 'i am a NOT token',
        }

        googleapi = self.get_googleapi('/?code=CODE')
        with self.assertRaises(AuthFailed):
            googleapi.exchange_token_from_code('http://redirect_uri.com')

        self.assertTrue(post.called)


@mock.patch('pyramid_google_login.utility.requests.get')
class TestUserinfoFromToken(TestUtility):

    def test_nominal(self, get):
        res = self.googleapi.get_userinfo_from_token({'access_token': 'TOKEN'})
        response = get.return_value
        self.assertEqual(response.json.return_value, res)

    def test_raises_exception(self, get):
        from pyramid_google_login.exceptions import AuthFailed
        get.side_effect = Exception('M*RDE!')
        with self.assertRaises(AuthFailed):
            self.googleapi.get_userinfo_from_token({'access_token': 'TOKEN'})


class TestCheckHostedDomainUser(TestUtility):

    def test_nominal(self):
        self.googleapi.check_hosted_domain_user({'hd': 'bob.com'})

    def test_no_hosted_domain(self):
        self.googleapi.hosted_domain = None
        self.assertIsNone(self.googleapi.check_hosted_domain_user({}))

    def test_empty_hosted_domain(self):
        self.googleapi.hosted_domain = ''
        self.assertIsNone(self.googleapi.check_hosted_domain_user({}))

    def test_not_same_domain(self):
        from pyramid_google_login.exceptions import AuthFailed
        with self.assertRaises(AuthFailed):
            self.googleapi.check_hosted_domain_user({'hd': 'not_bob.com'})

    def test_no_hd_in_userinfo(self):
        from pyramid_google_login.exceptions import AuthFailed
        with self.assertRaises(AuthFailed):
            self.googleapi.check_hosted_domain_user({'not_hd': 'whatever'})


class TestGetUserIdFromUserinfo(TestUtility):

    def test_nominal(self):
        self.assertEqual(
            'bob@bob.com',
            self.googleapi.get_user_id_from_userinfo({'email': 'bob@bob.com'})
            )

    def test_key_error(self):
        from pyramid_google_login.exceptions import AuthFailed
        with self.assertRaises(AuthFailed):
            self.googleapi.get_user_id_from_userinfo({'nope': 'whatever'})
