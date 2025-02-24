import os

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import toml

def logger_info(message:str):
    "Log message in a server."
    url = toml.load("log_config.toml")["url"]+"/log"
    httpx.request(method="POST", url=url, json={"message":message})
    
logger_info("aggregator starting")

CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", "../config.yaml")

with open(CONFIG_FILE_PATH, "r") as f:
    config_data = yaml.safe_load(f)

# Define the host and port for the hardware, browser, and aggregator services
HARDWARE_HOST = config_data["hardware_service"]["host"]
HARDWARE_PORT = config_data["hardware_service"]["port"]
BROWSER_HOST = config_data["browser_service"]["host"]
BROWSER_PORT = config_data["browser_service"]["port"]
AGGREGATOR_HOST = config_data["aggregator_service"]["host"]
AGGREGATOR_PORT = config_data["aggregator_service"]["port"]
AGGREGATOR_RELOAD = config_data["aggregator_service"].get("reload", False)

# Define the URLs for the hardware and browser services
HARDWARE_URL = f"http://{HARDWARE_HOST}:{HARDWARE_PORT}"
BROWSER_URL = f"http://{BROWSER_HOST}:{BROWSER_PORT}"


class SearchQuery(BaseModel):
    query: str


app = FastAPI()

# Add CORS Middleware if needed, idk so I'm just gonna leave it here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/capture")
def capture() -> Response:
    """
    Proxy to /capture on the hardware service.
    Returns the PNG image from the hardware service directly.
    """
    try:
        resp = httpx.get(f"{HARDWARE_URL}/capture")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        logger_info("capture request sent")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/png"),
        )
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot")
def screenshot() -> Response:
    """
    Proxy to /screenshot on the hardware service.
    Returns the PNG screenshot directly.
    """
    try:
        resp = httpx.get(f"{HARDWARE_URL}/screenshot")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        logger_info("screenshot request sent")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/png"),
        )
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cpu")
def cpu() -> JSONResponse:
    """
    Proxy to /cpu on the hardware service.
    """
    try:
        resp = httpx.get(f"{HARDWARE_URL}/cpu")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        logger_info("cpu info request sent")
        return JSONResponse(content=resp.json())
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disk")
def disk() -> JSONResponse:
    """
    Proxy to /disk on the hardware service.
    """
    try:
        resp = httpx.get(f"{HARDWARE_URL}/disk")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        logger_info("disk info request sent")
        return JSONResponse(content=resp.json())
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ram")
def ram() -> JSONResponse:
    """
    Proxy to /ram on the hardware service.
    """
    try:
        resp = httpx.get(f"{HARDWARE_URL}/ram")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        logger_info("ram info request sent")
        return JSONResponse(content=resp.json())
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/all_hardware_info")
def all_hardware_info() -> JSONResponse:
    """
    Call the urls /ram, /disk, /cpu on the hardware service.
    """
    try:
        resp_ram = httpx.get(f"{HARDWARE_URL}/ram")
        resp_disk = httpx.get(f"{HARDWARE_URL}/disk")
        resp_cpu = httpx.get(f"{HARDWARE_URL}/cpu")
        if resp_ram.status_code != 200:
            raise HTTPException(status_code=resp_ram.status_code, detail=resp_ram.text)
        if resp_disk.status_code != 200:
            raise HTTPException(status_code=resp_disk.status_code, detail=resp_disk.text)
        if resp_cpu.status_code != 200:
            raise HTTPException(status_code=resp_cpu.status_code, detail=resp_cpu.text)
        logger_info("all hardware info request sent")
        return JSONResponse(
            content={
                "ram": resp_ram.json(),
                "disk": resp_disk.json(),
                "cpu": resp_cpu.json(),
            }
        )
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/new_window_and_search")
def new_window_and_search(query: SearchQuery) -> dict:
    """
    Proxy to /browser/new_window_and_search on the browser service.
    """
    try:
        resp = httpx.post(f"{BROWSER_URL}/browser/new_window_and_search", json=query.dict())
        logger_info("new window and search request sent")
        return resp.json()  # returns a dict
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/open_new_window")
def open_new_window() -> dict:
    """
    Proxy to /browser/open_new_window on the browser service.
    """
    try:
        resp = httpx.post(f"{BROWSER_URL}/browser/open_new_window")
        logger_info("open window request sent")
        return resp.json()  # returns a dict
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search(query: SearchQuery) -> dict:
    """
    Proxy to /browser/search on the browser service.
    """
    try:
        resp = httpx.post(f"{BROWSER_URL}/browser/search", json=query.dict())
        logger_info("search request sent")
        return resp.json()  # returns a dict
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close_current_window")
def close_current_window() -> dict:
    """
    Proxy to /browser/close_current_window on the browser service.
    """
    try:
        resp = httpx.post(f"{BROWSER_URL}/browser/close_current_window")
        logger_info("close window request sent")
        return resp.json()  # returns a dict
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close_browser")
def close_browser() -> dict:
    """
    Proxy to /browser/close_browser on the browser service.
    """
    try:
        resp = httpx.post(f"{BROWSER_URL}/browser/close_browser")
        logger_info("close browser request sent")
        return resp.json()  # returns a dict
    except Exception as e:
        logger_info(f"exception {e} encountered")
        raise HTTPException(status_code=500, detail=str(e))


logger_info("starting node...")
if __name__ == "__main__":
    uvicorn.run(
        "aggregator:app",
        host=AGGREGATOR_HOST,
        port=AGGREGATOR_PORT,
        reload=AGGREGATOR_RELOAD,
    )
