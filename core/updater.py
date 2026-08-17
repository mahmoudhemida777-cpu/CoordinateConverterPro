"""Lightweight GitHub Releases updater for the portable Windows build."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "mahmoudhemida777-cpu/CoordinateConverterPro"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_URL = f"https://github.com/{REPO}/releases/latest/download/MH_Coordinate-Windows.zip"


def _version_tuple(value: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", value or "0")
    return tuple(int(x) for x in nums[:4]) or (0,)


def latest_release() -> tuple[str, str] | None:
    try:
        req = urllib.request.Request(LATEST_API, headers={"User-Agent": "MH-Coordinate"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        title = str(data.get("name", "")).strip()
        match = re.search(r"v?(\d+(?:\.\d+){1,3})", title)
        version = match.group(1) if match else ""
        if not version:
            return None
        return version, str(data.get("html_url", ""))
    except Exception:
        return None


def check_for_update(current_version: str) -> tuple[str, str] | None:
    latest = latest_release()
    if not latest:
        return None
    version, page_url = latest
    if _version_tuple(version) <= _version_tuple(current_version):
        return None
    return version, page_url


def install_latest_windows(parent=None) -> bool:
    """Download latest release and replace the running portable EXE after exit."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return False

    app_exe = Path(sys.executable).resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix="mh_coordinate_update_"))
    zip_path = temp_dir / "update.zip"
    extract_dir = temp_dir / "new"
    try:
        req = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": "MH-Coordinate"})
        with urllib.request.urlopen(req, timeout=120) as response, open(zip_path, "wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        candidates = list(extract_dir.rglob("MH_Coordinate.exe"))
        if not candidates:
            return False
        new_exe = candidates[0].resolve()

        ps1 = temp_dir / "apply_update.ps1"
        script = f'''$pidToWait = {os.getpid()}\n$newExe = '{str(new_exe).replace("'", "''")}'\n$target = '{str(app_exe).replace("'", "''")}'\nfor ($i=0; $i -lt 60; $i++) {{\n  try {{ Get-Process -Id $pidToWait -ErrorAction Stop | Out-Null; Start-Sleep -Milliseconds 500 }} catch {{ break }}\n}}\nStart-Sleep -Seconds 1\nCopy-Item -LiteralPath $newExe -Destination $target -Force\nStart-Process -FilePath $target\nRemove-Item -LiteralPath '{str(temp_dir).replace("'", "''")}' -Recurse -Force -ErrorAction SilentlyContinue\n'''
        ps1.write_text(script, encoding="utf-8")
        subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception:
        return False
