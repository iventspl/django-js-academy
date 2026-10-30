#!/usr/bin/env python3
"""One-command local launcher for Django Quest (macOS + Windows + Linux).

It creates a private virtual environment, installs Django on first run, applies
migrations, loads the bundled content, and starts the development server at a
free local port. No global Python packages are needed.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import socket
import subprocess
import sys
import threading
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
MIN_PYTHON = (3, 10)


def fail(message: str) -> None:
    print(f"\n[error] {message}\n", file=sys.stderr)
    raise SystemExit(1)


def lan_ipv4_addresses() -> list[str]:
    """Return private IPv4 addresses usable by another device on the LAN."""
    candidates: set[str] = set()

    # This UDP connect does not send packets, but asks the OS which local
    # interface would be used for outbound traffic.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidates.add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.add(info[4][0])
    except OSError:
        pass

    usable: list[str] = []
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_private and not address.is_loopback and not address.is_link_local:
            usable.append(candidate)
    return sorted(usable)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run(args: list[str], *, cwd: Path = ROOT, check: bool = True, quiet: bool = False):
    return subprocess.run(
        args,
        cwd=str(cwd),
        check=check,
        capture_output=quiet,
        text=True,
    )


def django_version(python: Path) -> str | None:
    try:
        result = run(
            [str(python), "-c", "import django; print(django.get_version())"],
            check=False,
            quiet=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip() or "installed"


def pip_available(python: Path) -> bool:
    try:
        result = run(
            [str(python), "-m", "pip", "--version"],
            check=False,
            quiet=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def create_venv(clear: bool = False) -> None:
    print("[setup] Creating a private virtual environment in .venv ...")
    builder = venv.EnvBuilder(
        with_pip=True,
        clear=clear,
        symlinks=os.name != "nt",
    )
    try:
        builder.create(str(VENV_DIR))
    except Exception as exc:  # venv creation can fail on unusual ACLs
        fail(
            "Could not create .venv. Make sure Python's venv module is available "
            f"and this folder is writable.\n\nDetails: {exc}"
        )


def install_requirements(python: Path) -> None:
    print("[setup] Installing Django (first run only) ...")
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    try:
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            cwd=str(ROOT),
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        fail(
            "Dependency installation failed. Check your internet connection, then "
            f"run this file again.\n\nDetails: {exc}"
        )


def ensure_environment() -> Path:
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. "
            f"You are running {sys.version.split()[0]}."
        )
    if not REQUIREMENTS.exists():
        fail("requirements.txt is missing. Run this script from the project folder.")

    python = venv_python()
    if not python.exists():
        create_venv(clear=VENV_DIR.exists())

    if django_version(python):
        return python

    if pip_available(python):
        install_requirements(python)
    else:
        # A half-created environment (for example after an interrupted setup)
        # is rebuilt rather than left in a broken state.
        print("[setup] Existing .venv is incomplete; rebuilding it ...")
        create_venv(clear=True)
        install_requirements(python)

    if not django_version(python):
        fail(
            "Django is still not importable after installation. Try deleting the "
            ".venv folder and running start.py again."
        )
    return python


def find_free_port(host: str, preferred: int) -> int:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    for port in range(preferred, preferred + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((check_host, port))
            except OSError:
                continue
            return port
    fail(f"No free port found between {preferred} and {preferred + 24}.")


def run_manage(python: Path, *args: str) -> None:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(python), str(ROOT / "manage.py"), *args],
        cwd=str(ROOT),
        env=env,
    )
    if result.returncode != 0:
        fail(f"manage.py {' '.join(args)} failed.")


def print_banner(url: str, lan_urls: list[str] | None = None) -> None:
    width = 46
    print()
    print("  +" + "-" * width + "+")

    def line(text: str) -> None:
        print("  |  " + f"{text:<{width - 2}}" + "|")

    line("DJANGO QUEST + JS AKADEMIA")
    print("  +" + "-" * width + "+")
    line(f"Local:  {url}")
    if lan_urls:
        for index, lan_url in enumerate(lan_urls):
            label = "LAN:    " if index == 0 else "        "
            line(f"{label}{lan_url}")
        line("Only use this on a trusted Wi-Fi network.")
        if os.name == "nt":
            line("Firewall: allow_lan_windows.bat (Admin)")
    line("Press Ctrl+C to stop the server.")
    print("  +" + "-" * width + "+")
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Start the local Django Quest app.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Preferred port (default: 8000)")
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Allow other devices on the local Wi-Fi/LAN to connect (binds 0.0.0.0).",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window.")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Upgrade Django and other requirements before starting.",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Install, migrate and seed, then exit without running the server.",
    )
    args = parser.parse_args()

    if not (0 < args.port < 65536):
        fail("--port must be between 1 and 65535.")

    python = ensure_environment()
    if args.update:
        install_requirements(python)
    version = django_version(python)
    print(f"[setup] Python {sys.version.split()[0]} | Django {version}")

    run_manage(python, "migrate", "--noinput")
    run_manage(python, "seed_content", "--if-changed")
    run_manage(python, "seed_js", "--if-changed")
    run_manage(python, "seed_ai", "--if-changed")
    print("[setup] Content is ready.")

    if args.setup_only:
        print("[done] Setup complete. Start with: python start.py")
        return

    lan_addresses: list[str] = []
    bind_host = args.host
    if args.lan:
        lan_addresses = lan_ipv4_addresses()
        if not lan_addresses:
            fail(
                "Could not detect a private IPv4 address. Connect to Wi-Fi and "
                "check your network adapter, then try again."
            )
        bind_host = "0.0.0.0"

    port = find_free_port(bind_host, args.port)
    display_host = "127.0.0.1" if bind_host in {"0.0.0.0", "::"} else bind_host
    url = f"http://{display_host}:{port}/"
    lan_urls = [f"http://{address}:{port}/" for address in lan_addresses]
    print_banner(url, lan_urls if args.lan else None)
    if not args.no_browser:
        threading.Timer(1.1, lambda: webbrowser.open(url)).start()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if args.lan:
        hostname = socket.gethostname()
        allowed_hosts = [
            "127.0.0.1",
            "localhost",
            "[::1]",
            "testserver",
            hostname,
            f"{hostname}.local",
            *lan_addresses,
        ]
        env["DJANGO_ALLOWED_HOSTS"] = ",".join(dict.fromkeys(allowed_hosts))
        origins = [f"http://{address}:{port}" for address in lan_addresses]
        origins.extend(
            [
                f"http://{hostname}:{port}",
                f"http://{hostname}.local:{port}",
            ]
        )
        env["DJANGO_CSRF_TRUSTED_ORIGINS"] = ",".join(dict.fromkeys(origins))
        print("[lan] Other devices can use the LAN URL above.")
        print("[lan] The app has no login: anyone on this Wi-Fi can read and change progress.")
    try:
        subprocess.run(
            [
                str(python),
                str(ROOT / "manage.py"),
                "runserver",
                f"{bind_host}:{port}",
                "--noreload",
            ],
            cwd=str(ROOT),
            env=env,
        )
    except KeyboardInterrupt:
        print("\n[stopped] Server stopped. Your progress is saved.")


if __name__ == "__main__":
    main()
