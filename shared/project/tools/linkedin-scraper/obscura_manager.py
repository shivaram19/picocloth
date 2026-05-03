"""
Obscura Manager – start/stop/health-check the Obscura headless browser.

Usage:
    from obscura_manager import ObscuraManager

    with ObscuraManager(port=9222, stealth=True) as obs:
        # Obscura is running on ws://127.0.0.1:9222
        ...
"""

import os
import sys
import time
import json
import signal
import socket
import subprocess
import atexit
from pathlib import Path
from typing import Optional


class ObscuraManager:
    """
    Manages the Obscura headless-browser binary.

    Looks for the binary in this order:
      1. ./obscura                      (downloaded release)
      2. ./obscura-src/target/release/obscura   (built from source)
      3. $PATH / `which obscura`
    """

    def __init__(
        self,
        port: int = 9222,
        stealth: bool = True,
        workers: int = 1,
        proxy: Optional[str] = None,
        obey_robots: bool = False,
        verbose: bool = True,
    ):
        self.port = port
        self.stealth = stealth
        self.workers = workers
        self.proxy = proxy
        self.obey_robots = obey_robots
        self.verbose = verbose

        self._process: Optional[subprocess.Popen] = None
        self._binary_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Binary discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _find_binary() -> Optional[str]:
        project_root = Path(__file__).parent.resolve()
        candidates = [
            project_root / "obscura",
            project_root / "obscura-src" / "target" / "release" / "obscura",
        ]
        for c in candidates:
            if c.exists() and os.access(c, os.X_OK):
                # Sanity-check: the binary must respond to --help without crashing
                try:
                    result = subprocess.run(
                        [str(c), "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and "Obscura" in result.stdout:
                        return str(c)
                except Exception:
                    continue

        # fallback to PATH
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            p = Path(path_dir) / "obscura"
            if p.exists() and os.access(p, os.X_OK):
                try:
                    result = subprocess.run(
                        [str(p), "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and "Obscura" in result.stdout:
                        return str(p)
                except Exception:
                    continue

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log(self, msg: str):
        if self.verbose:
            print(f"[ObscuraManager] {msg}", flush=True)

    def _is_port_open(self, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, self.port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _wait_for_ready(self, timeout: float = 30.0) -> bool:
        """Poll until the CDP HTTP endpoint answers."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._is_port_open():
                # Also try the JSON list endpoint to be sure CDP is up
                try:
                    import urllib.request
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{self.port}/json/list",
                        timeout=2,
                    ) as resp:
                        if resp.status == 200:
                            return True
                except Exception:
                    pass
            time.sleep(0.3)
        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> str:
        """
        Start the Obscura server.

        Returns:
            WebSocket endpoint URL, e.g. ``ws://127.0.0.1:9222``
        """
        binary = self._find_binary()
        if not binary:
            raise RuntimeError(
                "Obscura binary not found.\n"
                "  • Download a release: curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz\n"
                "  • Or build from source: cargo build --release --features stealth"
            )
        self._binary_path = binary

        if self._is_port_open():
            self._log(f"Port {self.port} already in use – assuming Obscura is already running.")
            return f"ws://127.0.0.1:{self.port}"

        cmd = [
            binary,
            "serve",
            "--port", str(self.port),
            "--workers", str(self.workers),
        ]
        if self.stealth:
            cmd.append("--stealth")
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.obey_robots:
            cmd.append("--obey-robots")

        self._log(f"Starting Obscura: {' '.join(cmd)}")
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Register an atexit hook so we don't leak the process on crash
        atexit.register(self.stop)

        if not self._wait_for_ready(timeout=30.0):
            self.stop()
            raise RuntimeError(
                f"Obscura did not become ready on port {self.port} within 30 s."
            )

        ws_url = f"ws://127.0.0.1:{self.port}"
        self._log(f"Obscura ready – endpoint: {ws_url}")
        return ws_url

    def stop(self):
        """Terminate the Obscura process if we started it."""
        if self._process is None:
            return

        self._log("Stopping Obscura …")
        proc = self._process
        self._process = None

        # Try graceful SIGTERM first
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._log("SIGTERM timed out – sending SIGKILL")
            proc.kill()
            proc.wait(timeout=2)
        except Exception as e:
            self._log(f"Error stopping Obscura: {e}")

        atexit.unregister(self.stop)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# ------------------------------------------------------------------
# Quick CLI health-check
# ------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Obscura manager utility")
    parser.add_argument("--start", action="store_true", help="Start Obscura server")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--stealth", action="store_true", default=True)
    parser.add_argument("--no-stealth", dest="stealth", action="store_false")
    args = parser.parse_args()

    if args.start:
        mgr = ObscuraManager(port=args.port, stealth=args.stealth)
        try:
            url = mgr.start()
            print(f"Obscura running at {url}")
            print("Press Ctrl+C to stop …")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            mgr.stop()
    else:
        binary = ObscuraManager._find_binary()
        if binary:
            print(f"Found Obscura binary: {binary}")
        else:
            print("Obscura binary NOT found.")
            sys.exit(1)


if __name__ == "__main__":
    main()
