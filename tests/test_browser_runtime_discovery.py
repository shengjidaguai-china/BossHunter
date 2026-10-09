"""Regression test for stale ``DevToolsActivePort`` handling in the browser runtime.

Chrome can leave a ``DevToolsActivePort`` file behind after a crash or upgrade.
The port it names often still accepts TCP connections, because some unrelated
process picked it up, but it no longer answers CDP. The runtime used to trust
that entry as soon as the TCP connect succeeded, so it never fell back to the
configured ``chrome_ports`` and every request failed, even when a healthy Chrome
was listening on 9222.

The runtime also has to accept the opposite shape: Chrome's default-profile
"Allow remote debugging" toggle (``chrome://inspect/#remote-debugging``) serves
the browser DevTools endpoint over WebSocket only and answers every ``/json/*``
request with 404. There the ``DevToolsActivePort`` path is the one piece of
usable information, so the runtime must use it - but only after proving it really
speaks CDP, otherwise the stale-port protection above is lost.

The test does not need Chrome:

* a decoy TCP listener holds the port named by ``DevToolsActivePort`` and replies
  with a body that is not a DevTools JSON document;
* a tiny fake DevTools endpoint (HTTP + WebSocket) stands in for Chrome on the
  configured ``chrome_ports``, optionally in WebSocket-only mode;
* the runtime has to skip the decoy and reach the fake endpoint.

Requires Node.js 22+ (same floor as the runtime); skipped otherwise.
"""

import base64
import contextlib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROXY_SCRIPT = REPO_ROOT / "src" / "bosshunter" / "browser" / "runtime" / "cdp-proxy.mjs"

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _node_executable():
    node = shutil.which("node")
    if not node:
        return None
    try:
        result = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        major = int((result.stdout or "").strip().lstrip("v").split(".")[0])
    except ValueError:
        return None
    return node if major >= 22 else None


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_ws_frame(conn, buffered=b""):
    """Read one masked client frame and return its payload."""
    buf = bytearray(buffered)

    def need(count):
        while len(buf) < count:
            chunk = conn.recv(4096)
            if not chunk:
                return False
            buf.extend(chunk)
        return True

    if not need(2):
        return None
    second = buf[1]
    length = second & 0x7F
    masked = bool(second & 0x80)
    offset = 2
    if length == 126:
        if not need(4):
            return None
        length = int.from_bytes(buf[2:4], "big")
        offset = 4
    elif length == 127:
        if not need(10):
            return None
        length = int.from_bytes(buf[2:10], "big")
        offset = 10
    mask = b""
    if masked:
        if not need(offset + 4):
            return None
        mask = bytes(buf[offset:offset + 4])
        offset += 4
    if not need(offset + length):
        return None
    payload = bytes(buf[offset:offset + length])
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return payload


def _text_frame(payload):
    header = bytearray([0x81])
    size = len(payload)
    if size < 126:
        header.append(size)
    elif size < 65536:
        header.append(126)
        header.extend(size.to_bytes(2, "big"))
    else:
        header.append(127)
        header.extend(size.to_bytes(8, "big"))
    return bytes(header) + payload


class _FakeCdp:
    """Minimal DevTools endpoint: ``/json/version`` plus a WebSocket that answers CDP.

    With ``ws_only=True`` it mimics the default-profile "Allow remote debugging"
    toggle from ``chrome://inspect``: ``/json/*`` answers 404 and only the browser
    WebSocket path recorded in ``DevToolsActivePort`` speaks CDP.
    """

    def __init__(self, ws_only=False):
        self.ws_path = "/devtools/browser/fake"
        self._ws_only = ws_only
        self._server = socket.socket()
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(8)
        self.port = int(self._server.getsockname()[1])
        self._stop = threading.Event()
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with contextlib.suppress(OSError, ValueError, KeyError):
            conn.settimeout(10)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                data += chunk
            head, _, rest = data.partition(b"\r\n\r\n")
            parts = head.split(b"\r\n", 1)[0].decode("latin-1", "ignore").split(" ")
            target = parts[1] if len(parts) > 1 else "/"

            if target.startswith("/json/version"):
                if self._ws_only:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                    return
                body = json.dumps({
                    "Browser": "Chrome/124.0.0.0",
                    "Protocol-Version": "1.3",
                    "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.port}{self.ws_path}",
                }).encode()
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
                )
                return

            key = ""
            for line in head.split(b"\r\n"):
                if line.lower().startswith(b"sec-websocket-key:"):
                    key = line.split(b":", 1)[1].strip().decode("latin-1")
            accept = base64.b64encode(hashlib.sha1((key + _WS_GUID).encode()).digest()).decode()
            conn.sendall(
                (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
                ).encode()
            )
            payload = _read_ws_frame(conn, rest)
            # Keep serving the session like Chrome does; closing after one reply
            # would reset the runtime's cached connection state under the client.
            while payload is not None:
                request = json.loads(payload.decode("utf-8"))
                if request.get("method") == "Browser.getVersion":
                    result = {"product": "Chrome/124.0.0.0"}
                else:
                    result = {"targetInfos": [{"targetId": "1", "type": "page", "url": "https://example.test/"}]}
                reply = json.dumps({"id": request.get("id"), "result": result}).encode()
                conn.sendall(_text_frame(reply))
                payload = _read_ws_frame(conn)
        with contextlib.suppress(OSError):
            conn.close()

    def close(self):
        self._stop.set()
        with contextlib.suppress(OSError):
            self._server.close()


class _DecoyTcpServer:
    """Accepts TCP and answers with a body that is not a DevTools JSON document."""

    def __init__(self):
        self._server = socket.socket()
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(8)
        self.port = int(self._server.getsockname()[1])
        self._stop = threading.Event()
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            with contextlib.suppress(OSError):
                conn.settimeout(5)
                conn.recv(4096)
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 9\r\n\r\nnot-json!")
            with contextlib.suppress(OSError):
                conn.close()

    def close(self):
        self._stop.set()
        with contextlib.suppress(OSError):
            self._server.close()


def _devtools_active_port_path(home):
    if sys.platform.startswith("win"):
        return home / "Google" / "Chrome" / "User Data" / "DevToolsActivePort"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Google" / "Chrome" / "DevToolsActivePort"
    return home / ".config" / "google-chrome" / "DevToolsActivePort"


def _http_json(url, timeout=3.0):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


class BrowserRuntimeDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = _node_executable()
        if not cls.node:
            raise unittest.SkipTest("needs Node.js 22+ (same floor as the bundled runtime)")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.decoy = _DecoyTcpServer()
        self.fake = _FakeCdp()
        self.proxy_port = _free_port()
        self.process = None

    def tearDown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.fake.close()
        self.decoy.close()
        self.tmp.cleanup()

    def _start_proxy_with_active_port_file(self, content, chrome_ports=None):
        port_file = _devtools_active_port_path(self.home)
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(content, encoding="utf-8")

        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["LOCALAPPDATA"] = str(self.home)
        env["BOSSHUNTER_BROWSER_PROXY_PORT"] = str(self.proxy_port)
        env["BOSSHUNTER_CHROME_PORTS"] = str(chrome_ports if chrome_ports is not None else self.fake.port)
        env["BOSSHUNTER_ENABLE_PORT_GUARD"] = "false"
        self.process = subprocess.Popen(
            [self.node, str(PROXY_SCRIPT)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

    def _start_proxy_with_stale_port_file(self):
        # What a stale file looks like: a live port that does not speak CDP.
        self._start_proxy_with_active_port_file(
            f"{self.decoy.port}\n/devtools/browser/stale\n",
            chrome_ports=self.fake.port,
        )

    def _wait_for_targets(self):
        base = f"http://127.0.0.1:{self.proxy_port}"
        deadline = time.time() + 25
        status = None
        last_error = None
        targets = None
        while time.time() < deadline:
            try:
                status, targets = _http_json(base + "/targets")
                break
            except (OSError, ValueError) as exc:
                last_error = exc
                time.sleep(0.4)

        self.assertIsNotNone(status, f"targets endpoint never answered: {last_error}")
        self.assertEqual(status, 200)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["url"], "https://example.test/")
        return base

    def test_stale_devtools_active_port_is_skipped(self):
        self._start_proxy_with_stale_port_file()
        base = self._wait_for_targets()

        _, health = _http_json(base + "/health")
        self.assertEqual(health["runtime"], "bosshunter")
        self.assertEqual(health["chromePort"], self.fake.port)

    def test_ws_only_devtools_active_port_is_used(self):
        """`chrome://inspect`'s "Allow remote debugging" exposes only the browser WebSocket."""
        self.fake.close()
        self.fake = _FakeCdp(ws_only=True)
        self._start_proxy_with_active_port_file(
            f"{self.fake.port}\n{self.fake.ws_path}\n",
            # The configured chrome_ports point at the decoy, so the WebSocket-only
            # entry is the only way discovery can succeed.
            chrome_ports=self.decoy.port,
        )
        base = self._wait_for_targets()

        deadline = time.time() + 10
        health = {}
        while time.time() < deadline:
            _, health = _http_json(base + "/health")
            if health.get("browserProduct"):
                break
            time.sleep(0.3)
        self.assertEqual(health["runtime"], "bosshunter")
        self.assertEqual(health["chromePort"], self.fake.port)
        self.assertEqual(health["connected"], True)
        self.assertEqual(health["browserProduct"], "Chrome/124.0.0.0")

    def test_decoy_port_is_not_a_devtools_endpoint(self):
        """Keep the fixture honest: the decoy must fail the /json/version probe."""
        with urllib.request.urlopen(f"http://127.0.0.1:{self.decoy.port}/json/version", timeout=5) as response:
            body = response.read()
        with self.assertRaises(json.JSONDecodeError):
            json.loads(body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
