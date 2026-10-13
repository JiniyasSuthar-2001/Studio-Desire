#!/usr/bin/env python3
"""
=============================================================================
STUDIO DESIRE — CENTRALIZED DEVELOPMENT STARTUP SYSTEM
=============================================================================

This script orchestrates and starts both:
1. Python / FastAPI backend (Uvicorn with --reload)
2. React / Vite frontend (npm run dev)

from a single terminal, streaming all output with clear [BACKEND] and 
[FRONTEND] prefixes, and gracefully shuts down both on Ctrl+C.

Usage:
    python start_up.py
"""

import sys
import os
import shutil
import signal
import atexit
import subprocess
import threading
import time
from pathlib import Path

# ANSI color codes for readable terminal logging
COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

# Enable VT100 colors in Windows console if supported
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

def print_banner():
    banner = f"""
{COLOR_BOLD}============================================================
 STUDIO DESIRE
 Development Environment Launcher
============================================================{COLOR_RESET}

  Backend:   http://127.0.0.1:8000
  API Docs:  http://127.0.0.1:8000/docs
  Frontend:  http://localhost:5173

{COLOR_YELLOW}[STARTUP]{COLOR_RESET} Press Ctrl+C at any time to stop both servers.
============================================================
"""
    print(banner.strip(), flush=True)

def log_startup(message: str, is_error: bool = False):
    tag_color = COLOR_RED if is_error else COLOR_YELLOW
    print(f"{tag_color}[STARTUP]{COLOR_RESET} {message}", flush=True)

def log_process(prefix: str, color: str, line: str):
    clean_line = line.rstrip("\r\n")
    if clean_line:
        print(f"{color}[{prefix}]{COLOR_RESET} {clean_line}", flush=True)

def stream_output(process: subprocess.Popen, prefix: str, color: str):
    """
    Reads process output line-by-line in a daemon thread and prints with prefix.
    """
    try:
        for raw_line in iter(process.stdout.readline, b""):
            if not raw_line:
                break
            try:
                line = raw_line.decode("utf-8", errors="replace")
            except Exception:
                line = str(raw_line)
            log_process(prefix, color, line)
    except Exception:
        pass
    finally:
        if process.stdout:
            try:
                process.stdout.close()
            except Exception:
                pass

def kill_process_tree(proc: subprocess.Popen, name: str):
    """
    Terminates a process and all its child processes cleanly (especially on Windows).
    """
    if proc is None or proc.poll() is not None:
        return

    pid = proc.pid
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass

backend_proc = None
frontend_proc = None
is_cleaning_up = False

def cleanup_all():
    global backend_proc, frontend_proc, is_cleaning_up
    if is_cleaning_up:
        return
    is_cleaning_up = True

    print(f"\n{COLOR_BOLD}============================================================{COLOR_RESET}")
    print("Stopping Studio Desire development servers...")

    if frontend_proc:
        kill_process_tree(frontend_proc, "frontend")
        print("Frontend stopped.")
        frontend_proc = None

    if backend_proc:
        kill_process_tree(backend_proc, "backend")
        print("Backend stopped.")
        backend_proc = None

    print("Studio Desire development environment stopped.")
    print(f"{COLOR_BOLD}============================================================{COLOR_RESET}")

atexit.register(cleanup_all)

def sig_handler(signum, frame):
    print(f"\n{COLOR_YELLOW}[STARTUP] Shutdown signal received...{COLOR_RESET}")
    cleanup_all()
    sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, sig_handler)

def main():
    project_root = Path(__file__).resolve().parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    print_banner()

    log_startup(f"Project root: {project_root}")
    log_startup(f"Python interpreter: {sys.executable}")

    # 1. Validate Backend
    if not backend_dir.exists() or not backend_dir.is_dir():
        log_startup(f"ERROR: Backend directory not found at: {backend_dir}", is_error=True)
        sys.exit(1)

    backend_entry = backend_dir / "app" / "main.py"
    if not backend_entry.exists():
        log_startup(f"ERROR: FastAPI entry point not found at: {backend_entry}", is_error=True)
        sys.exit(1)

    log_startup(f"Backend directory: OK ({backend_dir})")

    # 2. Validate Frontend
    if not frontend_dir.exists() or not frontend_dir.is_dir():
        log_startup(f"ERROR: Frontend directory not found at: {frontend_dir}", is_error=True)
        sys.exit(1)

    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        log_startup(f"ERROR: Frontend package.json not found at: {package_json}", is_error=True)
        sys.exit(1)

    log_startup(f"Frontend directory: OK ({frontend_dir})")

    # 3. Validate Node / npm
    npm_cmd = shutil.which("npm.cmd") if sys.platform == "win32" else shutil.which("npm")
    if not npm_cmd:
        npm_cmd = shutil.which("npm")

    if not npm_cmd:
        log_startup(
            "ERROR: 'npm' executable not found in PATH.\n"
            "Please install Node.js and ensure npm is available in your environment.",
            is_error=True
        )
        sys.exit(1)

    log_startup(f"npm binary: OK ({npm_cmd})")
    log_startup("All preflight checks passed. Starting servers...\n")

    # Environment variables
    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"
    backend_env["PYTHONIOENCODING"] = "utf-8"

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    backend_env["PYTHONPATH"] = (
        f"{backend_dir}{os.pathsep}{project_root}"
        + (f"{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "")
    )

    frontend_env = os.environ.copy()

    # Commands
    backend_args = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload"
    ]

    frontend_args = [npm_cmd, "run", "dev"]

    global backend_proc, frontend_proc
    backend_proc = None
    frontend_proc = None

    try:
        # Start Backend
        log_process("BACKEND", COLOR_CYAN, "Starting FastAPI (Uvicorn)...")
        backend_proc = subprocess.Popen(
            backend_args,
            cwd=str(backend_dir),
            env=backend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Start Frontend
        log_process("FRONTEND", COLOR_GREEN, "Starting React / Vite dev server...")
        frontend_proc = subprocess.Popen(
            frontend_args,
            cwd=str(frontend_dir),
            env=frontend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Start background reader threads
        backend_thread = threading.Thread(
            target=stream_output,
            args=(backend_proc, "BACKEND", COLOR_CYAN),
            daemon=True
        )
        frontend_thread = threading.Thread(
            target=stream_output,
            args=(frontend_proc, "FRONTEND", COLOR_GREEN),
            daemon=True
        )

        backend_thread.start()
        frontend_thread.start()

        # Monitor loop
        while True:
            time.sleep(0.5)

            # Check if backend exited unexpectedly
            backend_exit = backend_proc.poll()
            if backend_exit is not None:
                print(f"\n{COLOR_RED}============================================================{COLOR_RESET}")
                print(f"{COLOR_RED}[BACKEND] PROCESS STOPPED (Exit code: {backend_exit}){COLOR_RESET}")
                print("The FastAPI backend has terminated unexpectedly.")
                print("Check the error log output above for details.")
                print(f"{COLOR_RED}============================================================{COLOR_RESET}")
                break

            # Check if frontend exited unexpectedly
            frontend_exit = frontend_proc.poll()
            if frontend_exit is not None:
                print(f"\n{COLOR_RED}============================================================{COLOR_RESET}")
                print(f"{COLOR_RED}[FRONTEND] PROCESS STOPPED (Exit code: {frontend_exit}){COLOR_RESET}")
                print("The frontend development server has terminated unexpectedly.")
                print("Check the error log output above for details.")
                print(f"{COLOR_RED}============================================================{COLOR_RESET}")
                break

    except KeyboardInterrupt:
        print(f"\n{COLOR_YELLOW}[STARTUP] Shutdown signal received (Ctrl+C)...{COLOR_RESET}")
    finally:
        print(f"\n{COLOR_BOLD}============================================================{COLOR_RESET}")
        print("Stopping Studio Desire development servers...")

        if frontend_proc:
            kill_process_tree(frontend_proc, "frontend")
            print("Frontend stopped.")

        if backend_proc:
            kill_process_tree(backend_proc, "backend")
            print("Backend stopped.")

        print("Studio Desire development environment stopped.")
        print(f"{COLOR_BOLD}============================================================{COLOR_RESET}")

if __name__ == "__main__":
    main()
