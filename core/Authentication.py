from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import RedirectResponse

from authlib.integrations.starlette_client import OAuth

from core.util import PLConfig as cfg

openid_url = 'https://accounts.google.com/.well-known/openid-configuration'

config = Config('.env')
oAuth = OAuth(config)
oAuth.register(
    name='google',
    client_id=cfg.client_id,
    client_secret=cfg.client_secret,
    server_metadata_url=openid_url,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

authRouter = APIRouter(
    prefix='',
    tags=['Authentication'],
)


class User(BaseModel):
    email: str
    full_name: Optional[str] = None
    picture: Optional[str] = None


@authRouter.route('/login')
async def login_via_google(request: Request):
    google = oAuth.create_client('google')
    redirect_uri = cfg.authRedirect
    return await google.authorize_redirect(request, redirect_uri)


@authRouter.route('/auth')
async def authorize_google(request: Request):
    google = oAuth.create_client('google')
    token = await google.authorize_access_token(request)
    user = await google.parse_id_token(request, token)

    request.session['user'] = user
    # do something with the token and profile
    return RedirectResponse('/', status_code=302)


@authRouter.route('/logout')
async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse('/')
