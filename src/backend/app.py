import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine

from backend.routers import health, prediction


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check the connection to the database
    if os.getenv("ENVIRONMENT") == "local":
        DATABASE_URL = "postgresql://user:password@db:5432/northwind"
    else:
        DATABASE_URL = "postgresql://user:password@0.0.0.0:5432/northwind"
    try:
        engine = create_engine(DATABASE_URL)
        engine.connect()
        logging.info("Database connection successful!")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise RuntimeError(f"Database connection failed: {e}")
    yield


app = FastAPI(
    title="Backend API for Data Analyst Agent",
    description="Backend API spec for Data Analyst Agent",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(prediction.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Data Analyst Agent Backend API"}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8002,
        reload=(True if os.getenv("ENVIRONMENT") == "local" else False),
    )
