"""Thin wrapper around python-osc for talking to AbletonOSC.

AbletonOSC listens on UDP 11000 and replies on UDP 11001 by default.
See https://github.com/ideoforms/AbletonOSC for the address namespace.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any

from pythonosc import dispatcher, osc_server, udp_client


@dataclass
class OSCConfig:
    host: str = "127.0.0.1"
    send_port: int = 11000
    recv_port: int = 11001


class AbletonOSC:
    """Synchronous request/response client for AbletonOSC.

    AbletonOSC's query addresses reply on the same address. We register a
    catch-all handler, push responses onto a queue, and let `query` block
    until a matching reply (or timeout) arrives.
    """

    def __init__(self, config: OSCConfig | None = None) -> None:
        self.config = config or OSCConfig()
        self._client = udp_client.SimpleUDPClient(self.config.host, self.config.send_port)
        self._responses: dict[str, Queue[tuple[Any, ...]]] = {}
        self._lock = threading.Lock()

        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self._on_message)
        self._server = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", self.config.recv_port), disp
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _on_message(self, address: str, *args: Any) -> None:
        with self._lock:
            q = self._responses.setdefault(address, Queue())
        q.put(args)

    def send(self, address: str, *args: Any) -> None:
        """Fire-and-forget OSC message."""
        self._client.send_message(address, list(args))

    def query(self, address: str, *args: Any, timeout: float = 1.0) -> tuple[Any, ...]:
        """Send a query and wait for the reply on the same address."""
        with self._lock:
            q = self._responses.setdefault(address, Queue())
            while not q.empty():
                q.get_nowait()
        self._client.send_message(address, list(args))
        try:
            return q.get(timeout=timeout)
        except Empty as e:
            raise TimeoutError(f"No OSC reply on {address} within {timeout}s") from e

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


_singleton: AbletonOSC | None = None


def get_client() -> AbletonOSC:
    global _singleton
    if _singleton is None:
        _singleton = AbletonOSC()
        time.sleep(0.05)  # let the receive thread bind
    return _singleton
