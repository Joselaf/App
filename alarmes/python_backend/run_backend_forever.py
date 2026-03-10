"""Simple watchdog to keep tuya_server.py running.

Restarts the backend process whenever it exits unexpectedly.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time


RESTART_DELAY_SECONDS = 5


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(base_dir, "tuya_server.py")

    if not os.path.exists(server_path):
        print(f"[watchdog] Backend file not found: {server_path}")
        return 1

    attempt = 0
    while True:
        attempt += 1
        print(f"[watchdog] Starting backend (attempt {attempt})...")

        try:
            process = subprocess.Popen([sys.executable, server_path], cwd=base_dir)
            exit_code = process.wait()
        except KeyboardInterrupt:
            print("[watchdog] Stopped by user")
            return 0
        except Exception as exc:
            print(f"[watchdog] Failed to launch backend: {exc}")
            exit_code = -1

        # Exit immediately if user terminated with Ctrl+C from child.
        if exit_code in (130, -2):
            print(f"[watchdog] Backend stopped by user (exit {exit_code})")
            return 0

        print(
            f"[watchdog] Backend exited with code {exit_code}. "
            f"Restarting in {RESTART_DELAY_SECONDS}s..."
        )
        time.sleep(RESTART_DELAY_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
