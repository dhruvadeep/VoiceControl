# Default Imports
import os

import requests
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", "config.yaml")

with open(CONFIG_FILE_PATH, "r") as f:
    config_data = yaml.safe_load(f)

# Extract the relevant fields from the YAML file
HARDWARE_HOST = config_data["hardware_service"]["host"]
HARDWARE_PORT = config_data["hardware_service"]["port"]
BROWSER_HOST = config_data["browser_service"]["host"]
BROWSER_PORT = config_data["browser_service"]["port"]

AGGREGATOR_HOST = config_data["aggregator_service"]["host"]
AGGREGATOR_PORT = config_data["aggregator_service"]["port"]
AGGREGATOR_RELOAD = config_data["aggregator_service"].get("reload", False)

# Build the base URLs for hardware and browser services
HARDWARE_URL = f"http://{HARDWARE_HOST}:{HARDWARE_PORT}"
BROWSER_URL = f"http://{BROWSER_HOST}:{BROWSER_PORT}"


###############################################################################
# 2. Define Pydantic Model(s) as needed
###############################################################################
class SearchQuery(BaseModel):
    query: str


###############################################################################
# 3. Create the FastAPI app
###############################################################################
app = FastAPI()

# Add CORS Middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


###############################################################################
# 4. Hardware Service Proxies
###############################################################################
@app.post("/capture")
def capture():
    """
    Proxy to /capture on the hardware service.
    Returns the PNG image from the hardware service directly.
    """
    try:
        resp = requests.get(f"{HARDWARE_URL}/capture")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/png"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot")
def screenshot():
    """
    Proxy to /screenshot on the hardware service.
    Returns the PNG screenshot directly.
    """
    try:
        resp = requests.get(f"{HARDWARE_URL}/screenshot")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/png"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cpu")
def cpu():
    """
    Proxy to /cpu on the hardware service.
    """
    try:
        resp = requests.get(f"{HARDWARE_URL}/cpu")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return JSONResponse(content=resp.json())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disk")
def disk():
    """
    Proxy to /disk on the hardware service.
    """
    try:
        resp = requests.get(f"{HARDWARE_URL}/disk")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return JSONResponse(content=resp.json())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ram")
def ram():
    """
    Proxy to /ram on the hardware service.
    """
    try:
        resp = requests.get(f"{HARDWARE_URL}/ram")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return JSONResponse(content=resp.json())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


###############################################################################
# 5. Browser Service Proxies
###############################################################################
@app.post("/new_window_and_search")
def new_window_and_search(query: SearchQuery):
    """
    Proxy to /browser/new_window_and_search on the browser service.
    """
    try:
        resp = requests.post(f"{BROWSER_URL}/browser/new_window_and_search", json=query.dict())
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/open_new_window")
def open_new_window():
    """
    Proxy to /browser/open_new_window on the browser service.
    """
    try:
        resp = requests.post(f"{BROWSER_URL}/browser/open_new_window")
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search(query: SearchQuery):
    """
    Proxy to /browser/search on the browser service.
    """
    try:
        resp = requests.post(f"{BROWSER_URL}/browser/search", json=query.dict())
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close_current_window")
def close_current_window():
    """
    Proxy to /browser/close_current_window on the browser service.
    """
    try:
        resp = requests.post(f"{BROWSER_URL}/browser/close_current_window")
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close_browser")
def close_browser():
    """
    Proxy to /browser/close_browser on the browser service.
    """
    try:
        resp = requests.post(f"{BROWSER_URL}/browser/close_browser")
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


###############################################################################
# 6. Run the Aggregator
###############################################################################
if __name__ == "__main__":
    uvicorn.run(
        "aggregator:app",
        host=AGGREGATOR_HOST,
        port=AGGREGATOR_PORT,
        reload=AGGREGATOR_RELOAD,
    )
