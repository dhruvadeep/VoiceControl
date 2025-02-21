"""control.py ."""

import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Union

import psutil
import yaml

SERVICES = {
    "browser": {
        "path": "browser_control",
        "commands": [
            "uv sync",
            "uv run playwright install firefox",
            "uv run uvicorn browser:APP --loop asyncio --host 0.0.0.0 --port 8001",
        ],
        "port": 8001,
        "config_key": "browser_service",
    },
    "hardware": {
        "path": "HardwareApplication",
        "commands": [
            "uv sync",
            "uv run hello.py",
        ],
        "port": 8003,
        "config_key": "hardware_service",
    },
    "transcriber": {
        "path": "transcriber",
        "commands": [
            "uv sync",
            "uv run transcriber.py",
        ],
        "port": 8005,
        "config_key": None,
    },
    "aggregator": {
        "path": "Application",
        "commands": [
            "uv sync",
            "uv run aggregator.py",
        ],
        "port": 8000,
        "config_key": "aggregator_service",
    },
}

processes = {}
executor = ThreadPoolExecutor(max_workers=4)
local_ip = ""


def get_local_ip() -> str:
    """Return the local IP address (e.g. 192.168.x.x)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def update_config() -> None:
    """Update Application/config.yaml so that 'host' entries match the current local IP."""
    global local_ip
    config_path = Path("Application/config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Update services that exist in config.yaml
    for service_key in ["hardware_service", "browser_service", "aggregator_service"]:
        if service_key in config:
            config[service_key]["host"] = local_ip

    with open(config_path, "w") as f:
        yaml.dump(config, f)


def run_service(service_name: str) -> None:
    """Run the service by executing each command in the service's 'commands' list.

    If the command includes 'uvicorn', 'hello.py', 'transcriber.py', or 'aggregator.py',
    it will be started via Popen (in the background).
    Otherwise, it will be run via subprocess.run() (blocking).
    """
    service = SERVICES[service_name]
    original_dir = os.getcwd()

    try:
        os.chdir(service["path"])
        for cmd in service["commands"]:
            # Check if this command should be run in the background
            if any(x in cmd for x in ["uvicorn", "hello.py", "transcriber.py", "aggregator.py"]):
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                processes[service_name] = process.pid
            else:
                # Blocking command, e.g. 'uv sync'
                subprocess.run(cmd, shell=True, check=True)
    finally:
        os.chdir(original_dir)
