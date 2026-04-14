#!/usr/bin/env python3
"""setup_env.py — Create venv and install dependencies for the drawthings skill.

Runs with the system Python. Requires Python 3.10+ and curl.
Will auto-install uv if not already on PATH.
Idempotent — safe to run repeatedly.

Usage:
    python scripts/setup_env.py

Outputs JSON to stdout:
    { "success": true/false, "venv_python": "...", "error": "..." }
"""

import json
import os
import subprocess
import shutil
import sys


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_uv():
    """Install uv if not on PATH. Returns path to uv binary."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # uv installs to ~/.local/bin/ by default
    local_bin = os.path.expanduser("~/.local/bin")
    candidate = os.path.join(local_bin, "uv")
    if os.path.isfile(candidate):
        return candidate

    # Auto-install via the official standalone installer
    if not shutil.which("curl"):
        return None

    install = subprocess.run(
        ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
        capture_output=True,
        timeout=60,
    )
    if install.returncode == 0 and os.path.isfile(candidate):
        return candidate

    return None


def main():
    root = _repo_root()
    venv_python = os.path.join(root, ".venv", "bin", "python")

    # Check Python version
    if sys.version_info < (3, 10):
        result = {
            "success": False,
            "error": f"Python >= 3.10 required, found {sys.version}",
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    # Ensure uv is available (auto-install if needed)
    uv = _ensure_uv()
    if not uv:
        result = {
            "success": False,
            "error": "uv could not be found or installed. Requires curl. Manual install: https://docs.astral.sh/uv/getting-started/installation/",
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    try:
        # Create venv (idempotent)
        subprocess.run(
            [uv, "venv", "--quiet"],
            cwd=root,
            check=True,
            capture_output=True,
        )

        # Install dependencies from pyproject.toml
        subprocess.run(
            [uv, "sync", "--quiet"],
            cwd=root,
            check=True,
            capture_output=True,
        )

        # Verify the package is importable
        verify = subprocess.run(
            [venv_python, "-c", "from drawthings.service import DTService"],
            capture_output=True,
            timeout=30,
        )
        if verify.returncode != 0:
            stderr_text = verify.stderr.decode().strip()
            result = {
                "success": False,
                "error": f"Dependencies installed but package import failed: {stderr_text}",
                "venv_python": venv_python,
            }
            print(json.dumps(result, indent=2), file=sys.stderr)
            sys.exit(1)

        result = {
            "success": True,
            "venv_python": venv_python,
            "repo_root": root,
        }
        print(json.dumps(result, indent=2))

    except subprocess.CalledProcessError as e:
        stderr_text = e.stderr.decode().strip() if e.stderr else str(e)
        result = {
            "success": False,
            "error": f"Setup failed: {stderr_text}",
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
