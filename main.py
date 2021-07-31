from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles

from typing import Optional
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from authlib.integrations.starlette_client import OAuth

import website.routes
from core import Jobs, Labels, Loss, Features, Hubs, Models, Authentication
from core.util import PLConfig as cfg
import core

app = FastAPI()

app.include_router(website.routes.router)

app.include_router(core.userRouter)

app.include_router(core.hubRouter)

app.include_router(core.trackRouter)

app.include_router(Jobs.routes.router)

app.include_router(core.otherRouter)

app.include_router(Authentication.authRouter)

app.add_middleware(SessionMiddleware, secret_key='secret')

app.mount("/static", StaticFiles(directory='website/static'), name='static')
app.mount('/{user}/{hub}', StaticFiles(directory='jbrowse/jbrowse'), name='jbrowseFiles')
