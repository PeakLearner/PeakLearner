import unittest

import mock


class TestIncludeme(unittest.TestCase):

    def test_includeme(self):
        from pyramid_google_login.views import includeme

        config = mock.Mock()

        includeme(config)

        expected_calls = [
            mock.call('auth_signin', '/auth/signin'),
            mock.call('auth_signin_redirect', '/auth/signin_redirect'),
            mock.call('auth_callback', '/auth/oauth2callback'),
            mock.call('auth_logout', '/auth/logout'),
        ]
        config.add_route.assert_has_calls(expected_calls, any_order=True)
        config.add_static_view.assert_called_once_with(
            'static/pyramid_google_login',
            'pyramid_google_login:static',
            cache_max_age=300)
        config.scan.assert_called_once_with('pyramid_google_login.views')


@mock.patch('pyramid_google_login.views.find_landing_path')
class TestSignin(unittest.TestCase):

    def setUp(self):
        self.request = mock.Mock()
        self.request.params = {
        }
        self.settings = {
            'security.google_login.client_id': 'CLIENTID',
            'security.google_login.client_secret': 'CLIENTSECRET',
            'googleapi_settings': mock.Mock(),
        }
        self.request.registry.settings = self.settings

        self.request.authenticated_userid = None
        self.request.route_url.return_value = '/test/url'

    def test_nominal(self, m_find_landing_path):
        from pyramid_google_login.views import signin

        resp = signin(self.request)

        googleapi_settings = (
            self.request.registry.settings['googleapi_settings']
            )

        expected = {'hosted_domain': googleapi_settings.hosted_domain,
                    'message': None,
                    'signin_advice': googleapi_settings.signin_advice,
                    'signin_banner': googleapi_settings.signin_banner,
                    'signin_redirect_url': '/test/url'}

        self.assertEqual(resp, expected)

    def test_authenticated(self, m_find_landing_path):
        from pyramid_google_login.views import signin
        from pyramid.httpexceptions import HTTPFound

        self.request.authenticated_userid = '123'

        resp = signin(self.request)

        self.assertIsInstance(resp, HTTPFound)
        self.assertEqual(resp.location, m_find_landing_path.return_value)

    def test_authenticated_with_url(self, m_find_landing_path):
        from pyramid_google_login.views import signin
        from pyramid.httpexceptions import HTTPFound

        self.request.params['url'] = '/go/there'
        self.request.authenticated_userid = '123'

        resp = signin(self.request)

        self.assertIsInstance(resp, HTTPFound)
        self.assertEqual(resp.location, '/go/there')


@mock.patch('pyramid_google_login.views.redirect_to_signin')
class TestLogout(unittest.TestCase):

    def setUp(self):
        self.request = mock.Mock()
        self.settings = {}
        self.request.registry.settings = self.settings

    def test_nominal(self, m_redirect):
        from pyramid_google_login.views import logout
        from pyramid_google_login.events import UserLoggedOut, Event

        resp = logout(self.request)

        self.assertEqual(resp, m_redirect.return_value)

        self.assertEqual(self.request.registry.notify.called, True)
        event = self.request.registry.notify.call_args[0][0]

        self.assertIsInstance(event, UserLoggedOut)
        self.assertIsInstance(event, Event)
        self.assertEqual(event.userid, self.request.unauthenticated_userid)
