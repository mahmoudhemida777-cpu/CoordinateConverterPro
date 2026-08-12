"""
Windows smoke test — runs ONLY on the GitHub Actions windows-latest
runner, against the actual PyInstaller-built EXE. It:

  1. Launches CoordinateConverterPro.exe
  2. Waits briefly for the Qt main window / event loop to come up
  3. Confirms the process is still alive (i.e. it did not crash on
     startup — no missing Qt DLL/plugin, no PROJ data error, etc.)
  4. Terminates it cleanly
  5. Exits non-zero on any failure, which fails the CI job and blocks
     packaging/installer/release steps from running (see build-windows.yml)

This is intentionally a startup/liveness smoke test, not a full UI test
suite — CI time budget and headless-Windows-runner constraints make full
UI automation out of scope for v1. The functional logic (CRS transforms,
parsers, exporters, validation, batch) is covered by tests/ via pytest in
the previous CI step, which runs before this one.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe-dir", required=True, help="Folder containing CoordinateConverterPro.exe")
    parser.add_argument("--startup-wait-seconds", type=float, default=6.0)
    args = parser.parse_args()

    exe_path = Path(args.exe_dir) / "CoordinateConverterPro.exe"
    if not exe_path.exists():
        print(f"FAIL: {exe_path} does not exist", file=sys.stderr)
        return 1

    print(f"Launching {exe_path} ...")
    proc = subprocess.Popen([str(exe_path)], cwd=str(args.exe_dir))

    time.sleep(args.startup_wait_seconds)

    if proc.poll() is not None:
        print(
            f"FAIL: process exited early with code {proc.returncode} "
            f"(crashed on startup — check logs/app.log)",
            file=sys.stderr,
        )
        return 1

    print("PASS: process is alive after startup wait window.")

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    log_path = Path(args.exe_dir) / "logs" / "app.log"
    if log_path.exists():
        print("---- app.log tail ----")
        print("\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]))
    else:
        print("NOTE: logs/app.log was not found next to the EXE.")

    print("Smoke test PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
