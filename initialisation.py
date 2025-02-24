# control.py
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil
import yaml

SERVICES = {
    "logger": {
        "path": "logging_server",
        "commands": [
            "uv sync",
            "uv run logger.py",
        ],
        "port": 8080,
        "config_key": "logger_service",
    },
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

# If each service has a log_config.toml, specify where to find them:
LOG_CONFIG_PATHS = {
    "logger": "logging_server/log_config.toml",  # If logger itself needs it
    "browser": "browser_control/log_config.toml",
    "hardware": "HardwareApplication/log_config.toml",
    "transcriber": "transcriber/log_config.toml",
    "aggregator": "Application/log_config.toml",
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
    """Update config.yaml so that 'host' entries match the current local IP
    for any known service key in SERVICES that has a config_key defined.
    """
    global local_ip
    config_path = Path("config.yaml")

    if not config_path.exists():
        print("No config.yaml found. Skipping config update.")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    # Update the relevant service hosts with our local IP.
    for service_name, svc_data in SERVICES.items():
        cfg_key = svc_data.get("config_key")
        if cfg_key:
            # If the config key doesn't exist at all, we might initialize it.
            if cfg_key not in config:
                config[cfg_key] = {"port": svc_data["port"]}
            config[cfg_key]["host"] = local_ip

    with open(config_path, "w") as f:
        yaml.dump(config, f)

def update_log_configs_with_logger_url() -> None:
    """After config.yaml is updated, read the logger service's host/port
    and update each service's log_config.toml to point to:
        url = "http://<logger_host>:<logger_port>"
    """
    config_path = Path("config.yaml")
    if not config_path.exists():
        return  # Nothing to do if config.yaml doesn't exist

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    # Fetch the logger service host/port from config
    logger_cfg = config.get("logger_service", {})
    logger_host = logger_cfg.get("host", "127.0.0.1")
    logger_port = logger_cfg.get("port", 8080)
    logger_url = f"http://{logger_host}:{logger_port}"

    # Update each log_config.toml file where it exists
    for svc, toml_path in LOG_CONFIG_PATHS.items():
        path_obj = Path(toml_path)
        if path_obj.exists():
            new_lines = []
            with open(path_obj) as fp:
                lines = fp.readlines()
            for line in lines:
                # Replace any line that starts with `url = `
                # (If your TOML has slightly different formatting, adjust as needed)
                if line.strip().startswith("url ="):
                    new_lines.append(f'url = "{logger_url}"\n')
                else:
                    new_lines.append(line)
            # Rewrite the file
            with open(path_obj, "w") as fp:
                fp.writelines(new_lines)

def run_service(service_name: str) -> None:
    """Run the service by executing each command in the service's 'commands' list
    inside a new terminal window (foreground) if it matches the usual 'long-running'
    commands (logger.py, uvicorn, hardware.py, etc.). Otherwise, run synchronously.

    Adjust the new-terminal logic for Windows (start cmd), macOS (osascript),
    or Linux (gnome-terminal) as needed.
    """
    service = SERVICES[service_name]
    original_dir = os.getcwd()

    try:
        os.chdir(service["path"])
        for cmd in service["commands"]:
            # List of known "long-running" commands we want in a new terminal:
            if any(x in cmd for x in ["logger.py", "uvicorn", "hardware.py", "transcriber.py", "aggregator.py"]):
                if os.name == "nt":  # Windows
                    process = subprocess.Popen(f"start cmd /k {cmd}", shell=True)
                elif sys.platform == "darwin":  # macOS
                    # Using osascript to open Terminal and run the command
                    process = subprocess.Popen(
                        f'osascript -e \'tell application "Terminal" to do script "{cmd}"\'',
                        shell=True,
                    )
                else:  # Linux (gnome-terminal). Adjust if using a different terminal
                    process = subprocess.Popen(f"gnome-terminal -- {cmd}", shell=True)

                processes[service_name] = process.pid
            else:
                # For short/one-shot commands (e.g., 'uv sync'):
                subprocess.run(cmd, shell=True, check=True)

    finally:
        os.chdir(original_dir)


def stop_service(service_name: str) -> bool:
    """Stop the service by killing its subprocess and any children."""
    if service_name in processes:
        try:
            pid = processes[service_name]
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            del processes[service_name]
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            print(f"Error stopping {service_name}: {e}")
    return False


def get_service_status() -> dict[str, dict[str, bool | str | int]]:
    """Return a dict with running status, host, port, and PID for each service."""
    status = {}
    for service_name, data in SERVICES.items():
        pid = processes.get(service_name)
        running = False
        if pid:
            try:
                psutil.Process(pid)  # Raises NoSuchProcess if not running
                running = True
            except psutil.NoSuchProcess:
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
    print("-" * 60)
    for name, info in status.items():
        state = "🟢 RUNNING" if info["running"] else "🔴 STOPPED"
        endpoint = f"http://{info['host']}:{info['port']}"
        pid_str = str(info["pid"]) if info["pid"] else "N/A"
        print(f"{name:<12} | {state:<8} | {endpoint:<25} | {pid_str}")


def show_menu() -> None:
    """Display the menu of control options."""
    print("\n🔧 Control Panel 🔧")
    print("1. Validate (Start) All Services Sequentially")
    print("2. Stop All Services")
    print("3. List Running Services")
    # Start service options
    for i, service in enumerate(SERVICES.keys(), start=4):
        print(f"{i}. Start {service.capitalize()} Service")
    stop_start = 4 + len(SERVICES)
    # Stop service options
    for i, service in enumerate(SERVICES.keys(), start=stop_start):
        print(f"{i}. Stop {service.capitalize()} Service")
    # Exit option
    print(f"{stop_start + len(SERVICES)}. Exit")


def handle_choice(choice: str) -> None:
    """Parse the user's numeric choice and call the appropriate function(s)."""
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
            stopped = stop_service(service_name)
            if not stopped:
                print(f"Service {service_name} was not running or could not be stopped.")
        # Exiting
        elif choice_int == (4 + len(SERVICES) * 2):
            print("👋 Exiting...")
            sys.exit(0)
        else:
            print("❌ Invalid choice")
    else:
        print("❌ Invalid choice")


def start_all_services() -> None:
    """Start all services *one by one* in a specific order:
    1) logger (first)
    2) browser
    3) hardware
    4) transcriber
    5) aggregator

    and wait ~10 seconds between each to let them spin up.
    """
    print("\n🚀 Starting all services in sequence...")

    # Define the order you want:
    service_order = ["logger", "browser", "hardware", "transcriber", "aggregator"]

    for svc in service_order:
        print(f"Starting {svc.capitalize()} service...")
        run_service(svc)
        print("Waiting 10 seconds to let the service fully start...\n")
        time.sleep(10)

    print("✅ All services have been started. Use option 3 to check status.")


def stop_all_services() -> None:
    """Stop all running services."""
    print("\n🛑 Stopping all services...")
    for svc in list(processes.keys()):
        stop_service(svc)
    print("✅ All services have been stopped. Use option 3 to check status.")


def start_service(service_name: str) -> None:
    """Start a single service in the background (new terminal)."""
    print(f"Starting {service_name} service...")
    executor.submit(run_service, service_name)
    time.sleep(1)  # Brief pause so we don't spam commands
    print("Use option 3 to check status.")


def main(choice: str) -> None:
    """Main entry that performs the action corresponding to the numeric choice.

    Examples:
      - main("1") => start all services sequentially
      - main("2") => stop all services
      - main("3") => print status

    """
    global local_ip
    local_ip = get_local_ip()
    update_config()  # Update the config.yaml with our local IP
    update_log_configs_with_logger_url() # update log files
    try:
        handle_choice(choice)
        while True:
            pass
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


if __name__ == "__main__":
    """
    By default, this will:
      1) Update config.yaml with your local IP
      2) Start ALL services sequentially (logger first, then others)
      3) Keep the script alive until you Ctrl+C, upon which all services are stopped.
    """
    try:
        main("1")  # Automatically "Validate (Start) All Services Sequentially"
    except KeyboardInterrupt:
        stop_all_services()
