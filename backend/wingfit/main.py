from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from . import __version__
from .config import settings
from .db.core import init_db
from .routers import admin, auth, blocs, categories, pr, programs
from .routers import settings as settings_r
from .routers import stash, statistics
from .utils.logging import request_logger
from .utils.date import dt_utc_str

if not Path(settings.FRONTEND_FOLDER).is_dir():
    raise ValueError()

Path(settings.ASSETS_FOLDER).mkdir(parents=True, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(blocs.router)
app.include_router(categories.router)
app.include_router(pr.router)
app.include_router(programs.router)
app.include_router(settings_r.router)
app.include_router(stash.router)
app.include_router(statistics.router)


@app.get("/api/info")
def info():
    return {"version": __version__}


@app.middleware("http")
async def http_logger__spa_handler(request: Request, call_next):
    response = await call_next(request)

    # Retrieve JWT second part, with properties
    bearer = request.headers.get("Authorization", ".").split(".")[1]

    # Keys are light to limit size
    # T: Datetime, M: Method, U: URL, A: Bearer, B: Body size, C: Resp. code, S: Resp. length, H: Host IP
    log_params = {
        "t": dt_utc_str(),
        "m": request.method,
        "u": str(request.url),
        "a": bearer,
        "b": request.headers.get("Content-Length"),
        "c": response.status_code,
        "s": response.headers.get("Content-Length"),
        "h": request.client.host,
    }
    request_logger.debug(str(log_params))

    if response.status_code == 404 and not request.url.path.startswith(("/api", "/assets")):
        return FileResponse(Path(settings.FRONTEND_FOLDER) / "index.html")
    return response


@app.on_event("startup")
def startup_event():
    init_db()


app.mount("/api/assets", StaticFiles(directory=settings.ASSETS_FOLDER), name="static")
app.mount("/", StaticFiles(directory=settings.FRONTEND_FOLDER, html=True), name="frontend")
