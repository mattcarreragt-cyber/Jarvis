import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.health import get_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

app = FastAPI(title="JARVIS OS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health():
    return await get_health()


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "JARVIS OS API", "docs": "/docs"}
