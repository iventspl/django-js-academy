#!/usr/bin/env python3
"""One-command local launcher for Django Quest (macOS + Windows + Linux).

It creates a private virtual environment, installs Django on first run, applies
migrations, loads the bundled content, and starts the development server at a
free local port. No global Python packages are needed.
"""

from __future__ import annotations

import argparse
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


def print_banner(url: str) -> None:
    print()
    print("  +----------------------------------------------+")
    print("  |  DJANGO QUEST + JS AKADEMIA                  |")
    print("  +----------------------------------------------+")
    print(f"  |  {url:<44}|")
    print("  |  Press Ctrl+C to stop the server.            |")
    print("  +----------------------------------------------+")
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Start the local Django Quest app.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Preferred port (default: 8000)")
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
    print("[setup] Content is ready.")

    if args.setup_only:
        print("[done] Setup complete. Start with: python start.py")
        return

    port = find_free_port(args.host, args.port)
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{display_host}:{port}/"
    print_banner(url)
    if not args.no_browser:
        threading.Timer(1.1, lambda: webbrowser.open(url)).start()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        subprocess.run(
            [
                str(python),
                str(ROOT / "manage.py"),
                "runserver",
                f"{args.host}:{port}",
                "--noreload",
            ],
            cwd=str(ROOT),
            env=env,
        )
    except KeyboardInterrupt:
        print("\n[stopped] Server stopped. Your progress is saved.")


if __name__ == "__main__":
    main()
