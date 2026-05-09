from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from typing import Tuple

import uvicorn

from autoee_demo.web_app import WebDemoSession, create_app, find_static_dir


_DEVNULL_HANDLES = []


def ensure_stdio() -> None:
    """PyInstaller windowed apps may set stdio streams to None."""

    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            handle = open(os.devnull, "w", encoding="utf-8")
            _DEVNULL_HANDLES.append(handle)
            setattr(sys, name, handle)


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_server(host: str, port: int, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for AutoEE server at {host}:{port}")


def start_server(host: str, port: int) -> Tuple[uvicorn.Server, threading.Thread]:
    ensure_stdio()
    session = WebDemoSession(min_module_seconds=2.0)
    app = create_app(session)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False, log_config=None)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="AutoEEWebServer", daemon=True)
    thread.start()
    wait_for_server(host, port)
    return server, thread


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the AutoEE Hardware Agent web desktop app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--browser", action="store_true", help="Open in the default browser instead of embedded WebView.")
    parser.add_argument("--smoke", action="store_true", help="Verify backend/static discovery and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ensure_stdio()
    args = parse_args(argv)
    if args.smoke:
        app = create_app(WebDemoSession(min_module_seconds=0.0))
        payload = app.state.session.state_payload()
        static_dir = find_static_dir()
        print("AutoEE web launcher smoke OK")
        print(f"static_dir={static_dir if static_dir else 'missing'}")
        print(f"workflow_status={payload.get('workflowStatus')}")
        print(f"stages={len(payload.get('stages', []))}")
        return 0

    host = str(args.host)
    port = int(args.port or find_free_port(host))
    server, thread = start_server(host, port)
    url = f"http://{host}:{port}/"
    print(f"AutoEE Hardware Agent is running at {url}")

    try:
        if args.browser:
            webbrowser.open(url)
            while thread.is_alive():
                time.sleep(0.5)
            return 0

        try:
            import webview  # type: ignore

            webview.create_window("AutoEE Hardware Agent", url, width=1440, height=900, min_size=(1100, 720))
            webview.start()
        except Exception as exc:
            print(f"Embedded WebView failed ({type(exc).__name__}: {exc}). Opening browser fallback.")
            webbrowser.open(url)
            while thread.is_alive():
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping AutoEE Hardware Agent...")
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
