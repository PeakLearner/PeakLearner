from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles

from typing import Optional
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from authlib.integrations.starlette_client import OAuth

from core.util import PLConfig as cfg

config = Config('.env')
oAuth = OAuth(config)
oAuth.register(
    name='google',
    client_id=cfg.client_id,
    client_secret=cfg.client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
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
    redirect_uri = request.url_for('authorize_google')
    return await google.authorize_redirect(request, redirect_uri)


@authRouter.route('/auth')
async def authorize_google(request: Request):
    google = oAuth.create_client('google')
    token = await google.authorize_access_token(request)
    user = await google.parse_id_token(request, token)

    request.session['user'] = user
    # do something with the token and profile
    return RedirectResponse('/')


@authRouter.route('/logout')
async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse('/')
