"""
KeyAuth System - HWID Fingerprinting
Cross-platform, zero-dependency hardware ID.
"""

import os
import sys
import uuid
import platform
import subprocess
import hashlib


def _wmic(args: str) -> str:
    """Windows WMI helper (returns '' on failure)."""
    try:
        out = subprocess.check_output(
            f"wmic {args}", shell=True, stderr=subprocess.DEVNULL, timeout=10
        )
        return out.decode(errors="ignore").strip()
    except Exception:
        return ""


def _run(cmd) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=10)
        return out.decode(errors="ignore").strip()
    except Exception:
        return ""


def _linux_machine_id() -> str:
    for path in ("/var/lib/dbus/machine-id", "/etc/machine-id"):
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return f.read().strip()
            except Exception:
                pass
    return ""


def get_hwid() -> str:
    """
    Return a stable, unique Hardware ID for this machine (SHA-256 of platform
    identifiers). Works on Windows / Linux / macOS without extra packages.
    """
    parts = []

    # --- Universal: node-based UUID ---
    try:
        parts.append(str(uuid.uuid3(uuid.NAMESPACE_DNS, platform.node())))
    except Exception:
        pass

    # --- Platform specific ---
    sysname = platform.system()
    if sysname == "Windows":
        parts.append(_wmic("csproduct get uuid").splitlines()[-1] if _wmic("csproduct get uuid") else "")
        parts.append(_wmic("baseboard get serialnumber").splitlines()[-1] if _wmic("baseboard get serialnumber") else "")
    elif sysname == "Linux":
        parts.append(_linux_machine_id())
        parts.append(_run(["cat", "/sys/class/dmi/id/product_uuid"]) or "")
    elif sysname == "Darwin":
        parts.append(_run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]) or "")

    raw = "|".join(p for p in parts if p)
    if not raw:
        raw = str(uuid.getnode())  # fallback: MAC address
    return hashlib.sha256(raw.encode()).hexdigest().upper()


if __name__ == "__main__":
    print(get_hwid())
