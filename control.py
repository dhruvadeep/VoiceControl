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

# Add a mapping from service -> path -> commands -> port -> config_key
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
    """Update config.yaml so that 'host' entries match the current local IP.
    If a service is missing, add it with its default port.
    """
    global local_ip
    config_path = Path("config.yaml")

    # Read existing config.yaml or create a new empty dict
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Update or create service entries in config
    for service_key, service in SERVICES.items():
        key = service["config_key"]
        if key:  # Only update if there's a config_key defined
            if key not in config:
                config[key] = {}
            config[key]["host"] = local_ip
            # Keep existing port if present, else set to default
            config[key].setdefault("port", service["port"])

    # Write back to config.yaml
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
    """Run the service by executing each command in the service's 'commands' list.

    If the command includes 'uvicorn', 'hardware.py', 'transcriber.py', 'aggregator.py', or 'logger.py',
    it will be started via Popen (in the background).
    Otherwise, it will be run via subprocess.run() (blocking).
    """
    service = SERVICES[service_name]
    original_dir = os.getcwd()

    try:
        os.chdir(service["path"])
        for cmd in service["commands"]:
            # Check if this command should be run in the background
            if any(x in cmd for x in ["uvicorn", "hardware.py", "transcriber.py", "aggregator.py", "logger.py"]):
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
    """Start all services *one by one*, in a specific order,
    ensuring logger runs first.
    """
    print("\n🚀 Starting all services in sequence...")
    update_log_configs_with_logger_url()
    # 1) Start logger first
    print("Starting Logger service first...")
    run_service("logger")
    print("Waiting a few seconds for the logger to fully start...")
    time.sleep(5)

    # 2) Then start the rest in your desired order
    service_order = ["browser", "hardware", "transcriber", "aggregator"]
    for svc in service_order:
        print(f"Starting {svc.capitalize()} service...")
        run_service(svc)
        print("Waiting a few seconds for the service to fully start...")
        time.sleep(5)

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

    # 1) Update config.yaml with local IP
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
