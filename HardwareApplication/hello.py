import asyncio
import uuid
from threading import Lock

import cv2
import pyautogui
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse

app = FastAPI()

# Global camera object and a lock to prevent concurrent access.
camera = None
camera_lock = Lock()


@app.on_event("startup")
async def startup_event():
    """
    On startup, open the camera and perform a warmup.
    If the camera cannot be opened or warmed up, raise an exception.
    """
    global camera
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise Exception("Error: Could not open camera at startup.")

    # Warm up the camera by reading and discarding a few frames.
    # Adjust the number of frames and delay as needed.
    for _ in range(10):
        ret, _ = camera.read()
        if not ret:
            raise Exception("Error: Could not warm up camera.")
        # Slight delay to allow the camera to adjust (if needed)
        await asyncio.sleep(0.1)

    print("Camera initialized and warmed up.")


@app.on_event("shutdown")
def shutdown_event():
    """
    On shutdown, release the camera resource.
    """
    global camera
    if camera is not None:
        camera.release()


@app.get("/capture")
async def capture():
    """
    Capture an image using the warmed-up camera and return it as a PNG image.
    """
    global camera
    if camera is None or not camera.isOpened():
        raise HTTPException(status_code=500, detail="Camera not available.")

    # Lock the camera access to avoid race conditions.
    with camera_lock:
        ret, frame = camera.read()

    if not ret:
        raise HTTPException(status_code=500, detail="Failed to capture image.")

    # Encode the captured frame as a PNG image in memory.
    success, encoded_image = cv2.imencode(".png", frame)
    if not success:
        raise HTTPException(status_code=500, detail="Could not encode image.")

    # Return the image as an in-memory response.
    return Response(content=encoded_image.tobytes(), media_type="image/png")


@app.get("/screenshot")
def screenshot():
    filename = f"./images/screenshot_{uuid.uuid4().hex}.png"
    image = pyautogui.screenshot()
    image.save(filename)
    return FileResponse(
        path=filename, media_type="image/png", filename="screenshot.png"
    )
