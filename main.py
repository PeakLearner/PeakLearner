from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


import website.routes
from core.util import PLConfig as cfg
from core import Jobs, Labels, Loss, Features, Hubs, Models, Authentication
import core

app = FastAPI()

app.include_router(website.routes.router)

app.include_router(core.userRouter)

app.include_router(core.hubRouter)

app.include_router(core.trackRouter)

app.include_router(Jobs.routes.router)

app.include_router(core.otherRouter)

app.include_router(Authentication.authRouter)

app.add_middleware(SessionMiddleware, secret_key=cfg.client_secret, max_age=600)

app.mount("/static", StaticFiles(directory='website/static'), name='static')
app.mount('/{user}/{hub}', StaticFiles(directory='jbrowse/jbrowse'), name='jbrowseFiles')