import sys
import os
import logging
import socket
import time
import random
import threading
import msvcrt
import subprocess
import psutil

from datetime import datetime
from colorama import init, Fore
from waitress import serve
from app import create_app, socketio
from zeroconf import ServiceInfo, Zeroconf

from rich.live import Live
from rich.table import Table
from rich.panel import Panel

init(autoreset=True)

# =========================
# PATH FIX
# =========================

if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.abspath(os.path.dirname(__file__))

os.chdir(BASE_PATH)

if not os.path.exists("instance"):
    os.makedirs("instance")

# =========================
# LOGGING
# =========================

log_file = os.path.join(BASE_PATH, "server.log")

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8")]
)

# =========================
# CREATE APP
# =========================

app = create_app()

# =========================
# DEV PANEL DATA
# =========================

start_time = time.time()
request_count = 0
connected_clients = set()

# =========================
# UTIL
# =========================

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# =========================
# LAN DISCOVERY
# =========================

def start_mdns_service(ip, port):

    zeroconf = Zeroconf()

    service_type = "_http._tcp.local."
    service_name = "Space_Share._http._tcp.local."

    info = ServiceInfo(
        service_type,
        service_name,
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/"},
        server="Space_Share.local."
    )

    zeroconf.register_service(info)

    print(Fore.CYAN + "[✓] LAN discovery enabled")
    print(Fore.CYAN + "Devices in the network can detect the server automatically")

    return zeroconf, info

# =========================
# HOT RELOAD
# =========================

WATCH_FOLDERS = ["templates", "static/css", "static/js"]
WATCH_FILES = ["app.py"]

def get_all_files():

    files = []

    for folder in WATCH_FOLDERS:

        path = os.path.join(BASE_PATH, folder)

        if os.path.exists(path):

            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    files.append(os.path.join(root, f))

    for f in WATCH_FILES:

        path = os.path.join(BASE_PATH, f)

        if os.path.exists(path):
            files.append(path)

    return files


def snapshot_files():

    snap = {}

    for f in get_all_files():
        try:
            snap[f] = os.path.getmtime(f)
        except:
            pass

    return snap


def watch_changes():

    snapshot = snapshot_files()

    while True:

        time.sleep(1)

        new_snapshot = snapshot_files()

        for file, mtime in new_snapshot.items():

            if file not in snapshot:
                reload_server(f"New file detected: {file}")

            elif snapshot[file] != mtime:
                reload_server(f"File changed: {file}")

        snapshot = new_snapshot


def reload_server(reason="Manual reload"):

    print(Fore.YELLOW + f"\n[RELOAD] {reason}")
    print(Fore.YELLOW + "Restarting server...\n")

    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable] + sys.argv)

    os._exit(0)

# =========================
# KEYBOARD CONTROL
# =========================

def keyboard_listener():

    while True:

        key = msvcrt.getch()

        try:
            key = key.decode("utf-8").lower()
        except:
            continue

        if key == "r":
            reload_server("Manual reload")

        elif key == "q":
            print(Fore.RED + "\n[SHUTDOWN] Server stopped")
            os._exit(0)

        elif key == "c":

            os.system("cls" if os.name == "nt" else "clear")
            spaceshare_splash()
            orbit_animation()
            print_logo()

        elif key == "l":

            ip = get_local_ip()
            port = 5000

            print(Fore.CYAN + "\nServer links:")
            print(Fore.CYAN + f"Local: http://127.0.0.1:{port}")
            print(Fore.CYAN + f"LAN:   http://{ip}:{port}")
            print(Fore.CYAN + f"DNS:   http://Space_Share.local:{port}\n")

# =========================
# DEV PANEL
# =========================

def build_dev_panel(ip, port):

    uptime = int(time.time() - start_time)

    memory = psutil.Process().memory_info().rss / 1024 / 1024

    table = Table(title="DEV SERVER PANEL")

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Uptime", f"{uptime} sec")
    table.add_row("Server", f"http://Space_Share.local:{port}")
    table.add_row("Requests", str(request_count))
    table.add_row("Clients", str(len(connected_clients)))
    table.add_row("Memory", f"{memory:.1f} MB")

    return Panel(table)


def start_dev_panel(ip, port):

    with Live(build_dev_panel(ip, port), refresh_per_second=1) as live:

        while True:

            live.update(build_dev_panel(ip, port))

            time.sleep(2)

# =========================
# STYLE OUTPUT
# =========================

def hacker_line(text, delay=0.01):

    for char in text:
        print(Fore.CYAN + char, end="", flush=True)
        time.sleep(delay)

    print()


def fake_loading(module):

    hacker_line(f"[+] Loading module: {module}")
    time.sleep(random.uniform(0.2, 0.5))
    hacker_line(f"[✓] {module} initialized")


def matrix_noise(duration=1):

    chars = "01"

    end_time = time.time() + duration

    while time.time() < end_time:

        line = "".join(random.choice(chars) for _ in range(60))

        print(Fore.CYAN + line)

        time.sleep(0.05)

# =========================
# LOGO
# =========================

def spaceshare_splash():

    frames = [
"""
        ✦
              ○

    SPACE
          SHARE

              ○
        ✦
""",
"""
              ✦
        ○

    SPACE
          SHARE

        ○
              ✦
""",
"""
        ○
              ✦

    SPACE
          SHARE

              ✦
        ○
"""
    ]

    for _ in range(6):
        for frame in frames:
            os.system("cls" if os.name == "nt" else "clear")
            print(Fore.CYAN + frame)
            time.sleep(0.15)

def orbit_animation(duration=2):

    frames = [
"""
          *
     .         .

        SPACESHARE

     .         .
          *
""",
"""
     *       .

        SPACESHARE

     .       *
""",
"""
     .       *

        SPACESHARE

     *       .
"""
    ]

    end = time.time() + duration

    while time.time() < end:

        for f in frames:
            os.system("cls" if os.name == "nt" else "clear")
            print(Fore.MAGENTA + f)
            time.sleep(0.2)

def print_logo():

    print(Fore.CYAN + r"""
   ███████╗██████╗  █████╗  ██████╗███████╗
   ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝
   ███████╗██████╔╝███████║██║     █████╗
   ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝
   ███████║██║     ██║  ██║╚██████╗███████╗
   ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝
""")

    print(Fore.MAGENTA + "        ███████╗██╗  ██╗ █████╗ ██████╗ ███████╗")
    print(Fore.MAGENTA + "        ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝")
    print(Fore.MAGENTA + "        ███████╗███████║███████║██████╔╝█████╗")
    print(Fore.MAGENTA + "        ╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝")
    print(Fore.MAGENTA + "        ███████║██║  ██║██║  ██║██║  ██║███████╗")
    print(Fore.MAGENTA + "        ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝")

    print()
    print(Fore.YELLOW + "        🚀 SpaceShare LAN Server")
    print(Fore.YELLOW + "        Secure • Fast • Local File Sharing")
    print()

# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    try:

        os.system("cls" if os.name == "nt" else "clear")

        spaceshare_splash()
        orbit_animation()
        print_logo()

        hacker_line("Booting SpaceShare server core...")
        matrix_noise()

        fake_loading("User Authentication")
        fake_loading("LAN Discovery")
        fake_loading("File Storage Engine")
        fake_loading("Share Link Generator")
        fake_loading("Security Sandbox")

        print()

        ip = get_local_ip()
        port = 5000

        print(Fore.CYAN + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(Fore.CYAN + f"🌐 SpaceShare Server Ready")
        print(Fore.CYAN + f"Local: http://127.0.0.1:{port}")
        print(Fore.CYAN + f"LAN:   http://{ip}:{port}")
        print(Fore.CYAN + f"DNS:   http://space_share.local:{port}")
        print(Fore.CYAN + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        print(Fore.RED + "R - reload | Q - quit | C - clear console | L - show links")
        print(Fore.YELLOW + "Auto reload enabled")
        print()

        start_mdns_service(ip, port)

        threading.Thread(target=watch_changes, daemon=True).start()
        threading.Thread(target=keyboard_listener, daemon=True).start()
        threading.Thread(target=start_dev_panel, args=(ip, port), daemon=True).start()

       
        socketio.run(app, host="0.0.0.0", port=5000)
        
    except Exception:

        logging.exception("Server crashed:")

        print(Fore.RED + "\n[CRITICAL] Server crashed! Check server.log")

        input("Press Enter to exit...")