#!/usr/bin/env python3
"""check_env.py — Validate runtime environment for the drawthings skill.

Runs with the system Python — no imports from drawthings.
Checks Python version, uv, venv, installed deps, and Draw Things server.

Usage:
    python scripts/check_env.py
    python scripts/check_env.py --host localhost:7859

Outputs JSON to stdout:
    { "ready": true/false, "checks": { ... }, "missing": [...] }
"""

import json
import os
import shutil
import socket
import subprocess
import sys


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _venv_python():
    return os.path.join(_repo_root(), ".venv", "bin", "python")


def check_python_version():
    """Python >= 3.10 required."""
    return sys.version_info >= (3, 10)


def check_curl():
    """curl on PATH (needed to auto-install uv)."""
    return shutil.which("curl") is not None


def check_uv():
    """uv package manager available (PATH or ~/.local/bin)."""
    if shutil.which("uv"):
        return True
    return os.path.isfile(os.path.expanduser("~/.local/bin/uv"))


def check_venv():
    """.venv exists with a usable Python binary."""
    return os.path.isfile(_venv_python())


def check_dependencies():
    """Core packages importable inside the venv."""
    venv_py = _venv_python()
    if not os.path.isfile(venv_py):
        return False
    try:
        result = subprocess.run(
            [venv_py, "-c", "import grpc, flatbuffers, google.protobuf, PIL"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_package_installed():
    """drawthings package importable inside the venv."""
    venv_py = _venv_python()
    if not os.path.isfile(venv_py):
        return False
    try:
        result = subprocess.run(
            [venv_py, "-c", "from drawthings.service import DTService"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_server(host="localhost", port=7859):
    """Draw Things gRPC server is reachable (TCP connect)."""
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except (OSError, socket.timeout):
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check drawthings skill environment")
    parser.add_argument("--host", default="localhost:7859", help="gRPC server address")
    args = parser.parse_args()

    host_str, _, port_str = args.host.partition(":")
    host = host_str or "localhost"
    port = int(port_str) if port_str else 7859

    checks = {
        "python_version": check_python_version(),
        "curl_available": check_curl(),
        "uv_installed": check_uv(),
        "venv_exists": check_venv(),
        "dependencies_installed": check_dependencies(),
        "package_importable": check_package_installed(),
        "server_reachable": check_server(host, port),
    }

    missing = [k for k, v in checks.items() if not v]
    # server_reachable is not required for setup — only for running scripts
    # uv_installed is not required — setup_env.py will auto-install it if curl is available
    setup_ready = all(
        v for k, v in checks.items() if k not in ("server_reachable", "uv_installed")
    )

    result = {
        "ready": setup_ready,
        "checks": checks,
        "missing": missing,
        "venv_python": _venv_python(),
        "repo_root": _repo_root(),
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if setup_ready else 1)


if __name__ == "__main__":
    main()
