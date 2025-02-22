# control.py
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
            "uv run hardware.py",
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
    """Update config.yaml so that 'host' entries match the current local IP."""
    global local_ip
    config_path = Path("config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Update services that exist in config.yaml
    for service_key in ["hardware_service", "browser_service", "aggregator_service"]:
        if service_key in config:
            config[service_key]["host"] = local_ip

    with open(config_path, "w") as f:
        yaml.dump(config, f)


def run_service(service_name: str) -> None:
    """
    Runs the service by executing each command in the service's 'commands' list.
    If the command includes 'uvicorn', 'hardware.py', 'transcriber.py', or 'aggregator.py',
    it will be started via Popen (in the background).
    Otherwise, it will be run via subprocess.run() (blocking).
    """
    service = SERVICES[service_name]
    original_dir = os.getcwd()

    try:
        os.chdir(service["path"])
        for cmd in service["commands"]:
            # Check if this command should be run in the background
            if any(x in cmd for x in ["uvicorn", "hardware.py", "transcriber.py", "aggregator.py"]):
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


def stop_service(service_name: str) -> bool:
    """Stops the service by killing its subprocess and any children."""
    if service_name in processes:
        try:
            pid = processes[service_name]
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            del processes[service_name]
            return True
        except Exception:
            return False
    return False


def get_service_status() -> dict[str, dict[str, Union[bool, str, int]]]:
    """Return a dict with running status, host, port, and PID for each service."""
    status = {}
    for service_name, data in SERVICES.items():
        pid = processes.get(service_name)
        running = False
        if pid:
            try:
                # If we can fetch the psutil.Process(pid), it's running
                psutil.Process(pid)
                running = True
            except psutil.NoSuchProcess:
                # If it fails, the process isn't actually running
                del processes[service_name]
        status[service_name] = {
            "running": running,
            "host": local_ip,
            "port": data["port"],
            "pid": pid,
        }
    return status


def print_status() -> None:
    """Pretty-print the status of all services."""
    status = get_service_status()
    print("\n📡 Service Status:")
    print(f"{'Service':<12} | {'Status':<8} | {'Endpoint':<25} | PID")
    print("-" * 50)
    for name, info in status.items():
        state = "🟢 RUNNING" if info["running"] else "🔴 STOPPED"
        endpoint = f"http://{info['host']}:{info['port']}"
        print(f"{name:<12} | {state:<8} | {endpoint:<25} | {info['pid'] or 'N/A'}")


def show_menu() -> None:
    """Display the menu of control options."""
    print("\n🔧 Control Panel 🔧")
    print("1. Validate (Start) All Services Sequentially")
    print("2. Stop All Services")
    print("3. List Running Services")
    # Start service options
    for i, service in enumerate(SERVICES.keys(), 4):
        print(f"{i}. Start {service.capitalize()} Service")
    stop_start = 4 + len(SERVICES)
    # Stop service options
    for i, service in enumerate(SERVICES.keys(), stop_start):
        print(f"{i}. Stop {service.capitalize()} Service")
    # Exit option
    print(f"{stop_start + len(SERVICES)}. Exit")


def handle_choice(choice: str) -> None:
    """
    Parse the user's numeric choice and call the appropriate
    function(s) to start/stop services or print status.
    """
    if choice == "1":
        start_all_services()
    elif choice == "2":
        stop_all_services()
    elif choice == "3":
        print_status()
    elif choice.isdigit():
        choice_int = int(choice)
        # Starting services
        if 4 <= choice_int <= 3 + len(SERVICES):
            service_index = choice_int - 4
            service_name = list(SERVICES.keys())[service_index]
            start_service(service_name)
        # Stopping services
        elif 4 + len(SERVICES) <= choice_int <= 3 + len(SERVICES) * 2:
            service_index = choice_int - (4 + len(SERVICES))
            service_name = list(SERVICES.keys())[service_index]
            stop_service(service_name)
        # Exiting
        elif choice_int == (4 + len(SERVICES) * 2):
            print("👋 Exiting...")
            sys.exit(0)
        else:
            print("❌ Invalid choice")
    else:
        print("❌ Invalid choice")


def start_all_services() -> None:
    """
    Starts all services *one by one*, in a specific order:
    browser → hardware → transcriber → aggregator
    and waits ~20 seconds between each.
    """
    print("\n🚀 Starting all services in sequence...")
    service_order = ["browser", "hardware", "transcriber", "aggregator"]

    for svc in service_order:
        print(f"Starting {svc.capitalize()} service...")
        run_service(svc)
        print("Waiting 20 seconds for the service to fully start...")
        time.sleep(20)

    print("✅ All services have been started. Use option 3 to check status.")


def stop_all_services() -> None:
    """Stop all running services."""
    print("\n🛑 Stopping all services...")
    for svc in list(processes.keys()):
        stop_service(svc)
    print("✅ All services have been stopped. Use option 3 to check status.")


def start_service(service_name: str) -> None:
    """Start a single service (placed in the background if it matches our condition)."""
    executor.submit(run_service, service_name)
    print(f"✅ {service_name} starting in the background...")
    time.sleep(1)  # Brief pause so we don't spam commands
    print("Use option 3 to check status.")


def main() -> None:
    global local_ip
    local_ip = get_local_ip()
    print(f"🔗 Detected Local IP: {local_ip}")
    update_config()

    while True:
        show_menu()
        try:
            choice = input("➡️  Select option: ")
            handle_choice(choice)
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}")
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
        sys.exit(0)
