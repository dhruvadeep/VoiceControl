import asyncio
import shutil
import uuid
from collections.abc import Awaitable, Callable
from threading import Lock

import cv2
import psutil
import pyautogui
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import Response as StarletteResponse
import httpx
import toml


app = FastAPI()

camera: cv2.VideoCapture | None = None
camera_lock: Lock = Lock()

def logger_info(message:str):
    "Log message in a server."
    url = toml.load("log_config.toml")["url"]+"/log"
    httpx.request(method="POST", url=url, json={"message":message})

@app.middleware("http")
async def add_cors_header(
    request: Request,
    call_next: Callable[[Request], Awaitable[StarletteResponse]],
) -> StarletteResponse:
    """Middleware to add CORS header to each response.
    Allows all origins (*). For production, specify allowed domains.
    """
    response: StarletteResponse = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    logger_info("adding cors headers")
    return response


@app.on_event("startup")
async def startup_event() -> None:
    """On startup, open the camera and perform a warmup.
    If the camera cannot be opened or warmed up, raise an exception.
    """
    global camera
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        logger_info("Could not open camera at startup.")
        raise Exception("Error: Could not open camera at startup.")
    logger_info("Camera initialized")
    # Warm up the camera by reading and discarding a few frames
    for _ in range(10):
        ret, _ = camera.read()
        if not ret:
            logger_info("Could not warmup camera")
            raise Exception("Error: Could not warm up camera.")
        # Slight delay to allow the camera to adjust (if needed)
        await asyncio.sleep(0.1)
    logger_info("Camera warmed up")
    print("Camera initialized and warmed up.")


@app.on_event("shutdown")
def shutdown_event() -> None:
    """On shutdown, release the camera resource if it exists."""
    global camera
    logger_info("shutting down camera")
    if camera is not None:
        camera.release()


@app.get("/capture")
async def capture() -> Response:
    """Capture an image using the warmed-up camera and return it as a PNG image."""
    global camera
    logger_info("capture request received")
    if camera is None or not camera.isOpened():
        logger_info("camera not available")
        raise HTTPException(status_code=500, detail="Camera not available.")

    # Lock the camera access to avoid race conditions
    with camera_lock:
        for _ in range(10):
            ret, frame = camera.read()
        ret, frame = camera.read()

    if not ret:
        logger_info("failed to capture image")
        raise HTTPException(status_code=500, detail="Failed to capture image.")

    # Encode the captured frame as a PNG image in memory
    success, encoded_image = cv2.imencode(".png", frame)
    if not success:
        logger_info("could not encode image")
        raise HTTPException(status_code=500, detail="Could not encode image.")
    logger_info("image captured")
    # Return the image as an in-memory response
    return Response(content=encoded_image.tobytes(), media_type="image/png")


@app.get("/screenshot")
def screenshot() -> FileResponse:
    """Take a screenshot of the current screen and return it as a PNG image file."""
    filename = f"./images/screenshot_{uuid.uuid4().hex}.png"
    image = pyautogui.screenshot()
    image.save(filename)
    logger_info("screenshot taken")
    return FileResponse(path=filename, media_type="image/png", filename="screenshot.png")


@app.get("/cpu")
def cpu() -> JSONResponse:
    """Returns the current CPU usage percentage."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    logger_info("cpu info obtained")
    return JSONResponse(content={"cpu_percent": cpu_percent})


def get_disk_usage() -> tuple[int, int, int]:
    """Returns disk usage (total, used, free) in bytes for the root path."""
    total, used, free = shutil.disk_usage("/")
    logger_info("disk info obtained")
    return total, used, free


def format_size(byte_size: float) -> str:
    """Formats a byte value into a human-readable string (e.g., B, KB, MB, GB, TB)."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if byte_size < 1024:
            return f"{byte_size:.2f}{unit}"
        byte_size /= 1024
    return f"{byte_size:.2f}PB"  # If it somehow exceeds TB


@app.get("/disk")
def disk() -> JSONResponse:
    """Returns disk usage information (total, used, free) in a formatted string."""
    total, used, free = get_disk_usage()
    return JSONResponse(
        content={
            "total": format_size(total),
            "used": format_size(used),
            "free": format_size(free),
        },
    )


@app.get("/ram")
def ram() -> JSONResponse:
    """Returns total, used, and available RAM in a formatted string."""
    total = psutil.virtual_memory().total
    available = psutil.virtual_memory().available
    used = total - available
    logger_info("ram info obtained")
    return JSONResponse(
        content={
            "total": format_size(total),
            "used": format_size(used),
            "available": format_size(available),
        },
    )


# get for no of cores, cpu arc, name
@app.get("/cpuinfo")
def cpuinfo() -> JSONResponse:
    """Returns the number of cores, CPU architecture, and name."""
    cpu_info = psutil.cpu_info()
    logger_info("cpu info obtained")
    return JSONResponse(
        content={
            "cores": cpu_info.cores,
            "arch": cpu_info.arch,
            "name": cpu_info.name,
        },
    )


###############################################################################
# 6. Run the Application
###############################################################################
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
