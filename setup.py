# control.py in main folder
import os
import socket
import subprocess
import sys
from pathlib import Path

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
        "commands": ["uv sync", "uv run hello.py"],
        "port": 8003,
        "config_key": "hardware_service",
    },
    "transcriber": {
        "path": "transcriber",
        "commands": ["uv sync", "uv run transcriber.py"],
        "port": 8005,
        "config_key": None,
    },
    "aggregator": {
        "path": "Application",
        "commands": ["uv sync", "uv run aggregator.py"],
        "port": 8000,
        "config_key": "aggregator_service",
    },
}


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def update_config(ip):
    config_path = Path("Application/config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    for service in ["hardware_service", "browser_service"]:
        config[service]["host"] = ip

    config["aggregator_service"]["host"] = ip

    with open(config_path, "w") as f:
        yaml.dump(config, f)


def run_service(service_name):
    service = SERVICES[service_name]
    print(f"\n🚀 Starting {service_name} service...")

    os.chdir(service["path"])
    for cmd in service["commands"]:
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error in {service_name}: {str(e)}")
            return False
    os.chdir("..")
    return True


def show_menu():
    print("\n🔧 Control Panel 🔧")
    print("1. Start All Services")
    for i, service in enumerate(SERVICES.keys(), 2):
        print(f"{i}. Start {service.capitalize()} Service")
    print(f"{len(SERVICES) + 2}. Exit")


def main():
    local_ip = get_local_ip()
    print(f"🔗 Detected Local IP: {local_ip}")
    update_config(local_ip)

    while True:
        show_menu()
        choice = input("➡️  Select option: ")

        if choice == "1":
            for service in SERVICES:
                if not run_service(service):
                    break
        elif choice in map(str, range(2, 2 + len(SERVICES))):
            service_index = int(choice) - 2
            service_name = list(SERVICES.keys())[service_index]
            run_service(service_name)
        elif choice == str(len(SERVICES) + 2):
            print("👋 Exiting...")
            break
        else:
            print("❌ Invalid choice")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
        sys.exit(0)
        sys.exit(0)
