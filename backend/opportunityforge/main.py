from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from os import getenv

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, create_engine

from opportunityforge.api.routes import router

DATABASE_URL = getenv(
    "DATABASE_URL",
    "sqlite:///./opportunityforge.db",
)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="OpportunityForge API",
    description="Public-data business opportunity intelligence API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://100.71.202.95:8000",
        "http://100.71.202.95:4173",
        "http://100.71.202.95:5173",
        getenv("FRONTEND_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

FRONTEND_BUILD = Path(__file__).resolve().parent.parent.parent / "frontend" / "build"
if FRONTEND_BUILD.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD), html=True), name="frontend")
