import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.scheduler import scheduler
from app.routers import door

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    task = asyncio.create_task(scheduler.start())
    yield
    scheduler.stop()
    task.cancel()


app = FastAPI(title="Garage Door Controller", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(door.router, prefix="/api/door")


@app.get("/api/health")
def health():
    return {"status": "ok"}
