from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

import website.routes
from core.util import PLConfig as cfg
# None of these are used explicitly but importing them causes the __init__.py file to start and import the routes
# The routes use the routers defined in core/__init__.py
from core import Jobs, Authentication, Features
import core

from . import database
database.do_create()

app = FastAPI()

app.include_router(website.routes.router)

app.include_router(core.userRouter)

app.include_router(core.hubRouter)

app.include_router(core.trackRouter)

app.include_router(Jobs.routes.router)

app.include_router(core.otherRouter)

app.include_router(Authentication.authRouter)

app.add_middleware(SessionMiddleware, secret_key=cfg.client_secret, max_age=600)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory='website/static'), name='static')
app.mount('/{user}/{hub}', StaticFiles(directory='jbrowse/jbrowse'), name='jbrowseFiles')
