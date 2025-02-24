import sys

import toml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

# request model


class LogRequest(BaseModel):
    message: str


# Load config
config = toml.load("config.toml")

# Configure Loguru
logger.remove()  # Remove default handler
logger.add(
    config["log"]["filename"],
    level=config["log"]["level"],
    rotation=config["log"]["rotation"],
    retention=config["log"]["retention"],
    compression=config["log"]["compression"],
    enqueue=True,
)
logger.add(sys.stderr, level="DEBUG")  # Also log to console

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests."""
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello, FastAPI with Loguru!"}


@app.post("/log")
async def log_message(message: LogRequest):
    logger.info(f"Logged message: {message.message}")
    return {"status": "logged", "message": message.message}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("__main__:app", host="0.0.0.0", port=8080, reload=True)
