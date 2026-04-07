"""
KVMShare – Client
=================
The secondary machine (receives mouse + keyboard from the server) runs this.

The client injects received events using pynput's Controller classes, which
work natively on both Windows (SendInput) and macOS (CGEventPost).

Edge detection
--------------
When the injected cursor reaches the LEFT edge of the client screen the
client sends {"t":"sw","dir":"to_server"} to hand control back.
"""

import logging
import socket
import threading
import time
from typing import Optional

from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button

from .config import Config
from .protocol import decode_from_buffer, encode
from .screen import get_screen_size

log = logging.getLogger(__name__)


class Client:
    def __init__(self, server_host: str, config: Config):
        self.server_host = server_host
        self.cfg = config
        self.sw, self.sh = get_screen_size()
        log.info("Screen: %dx%d", self.sw, self.sh)

        self._mouse = mouse.Controller()
        self._kbd = keyboard.Controller()

        # Start cursor at centre of screen
        self._mouse.position = (self.sw // 2, self.sh // 2)

        self._active = False      # True = this client has control (protegido por _lock)
        self._conn: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._last_return = 0.0   # timestamp del último return edge (cooldown)
        self._pressed_keys: set = set()  # teclas actualmente inyectadas

        self._hotkey_listener = self._build_hotkey_listener()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self):
        if self._hotkey_listener:
            self._hotkey_listener.start()
            log.info("Return hotkey active: %s", self.cfg.return_hotkey)
        while True:
            try:
                self._connect_and_loop()
            except Exception as exc:
                log.error("Connection error: %s – retrying in 5 s", exc)
                time.sleep(5)

    # ------------------------------------------------------------------
    # TCP
    # ------------------------------------------------------------------

    def _connect_and_loop(self):
        log.info("Connecting to %s:%d …", self.server_host, self.cfg.port)
        conn = socket.create_connection(
            (self.server_host, self.cfg.port), timeout=10
        )
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # TCP keepalive: OS detecta conexiones muertas sin depender de pings
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        try:
            import ctypes
            TCP_KEEPALIVE = 0x10  # macOS
            conn.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 10)
        except Exception:
            pass
        # Timeout en recv: si no llega nada en ping_interval*3s, la conexión murió
        conn.settimeout(self.cfg.ping_interval * 3)
        with self._lock:
            self._conn = conn
        log.info("Connected – waiting for control handoff")
        self._recv_loop(conn)

    def _recv_loop(self, conn: socket.socket):
        buf = bytearray()
        while True:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                log.warning("No data received – connection stale, reconnecting")
                break
            except OSError:
                chunk = b""
            if not chunk:
                log.info("Server closed connection")
                break
            buf.extend(chunk)
            while True:
                event, buf = decode_from_buffer(buf)
                if event is None:
                    break
                self._dispatch(event)

        with self._lock:
            self._active = False
            self._conn = None

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, event: dict):
        t = event.get("t")

        if t == "ping":
            return

        if t == "mv":
            self._on_move(event["dx"], event["dy"])
        elif t == "mc":
            self._on_click(event["b"], event["p"])
        elif t == "ms":
            self._on_scroll(event["dx"], event["dy"])
        elif t == "kp":
            self._on_key(event["k"], event["p"])

        # First event that isn't a ping means we now have control
        with self._lock:
            if not self._active and t in ("mv", "mc", "ms", "kp"):
                self._active = True
                log.info("Control received")

    # ------------------------------------------------------------------
    # Input injection
    # ------------------------------------------------------------------

    def _on_move(self, dx: int, dy: int):
        cx, cy = self._mouse.position
        nx = max(0, min(self.sw - 1, cx + dx))
        ny = max(0, min(self.sh - 1, cy + dy))
        self._mouse.position = (nx, ny)

        # Return edge is the opposite of remote_position
        ep = self.cfg.edge_px
        pos = self.cfg.remote_position
        triggered = (
            (pos == "right"  and nx <= ep) or
            (pos == "left"   and nx >= self.sw - ep) or
            (pos == "above"  and ny >= self.sh - ep) or
            (pos == "below"  and ny <= ep)
        )
        if triggered:
            now = time.monotonic()
            with self._lock:
                if not self._active or (now - self._last_return) < 1.0:
                    return  # cooldown: evita re-trigger si cursor oscila en el borde
                self._active = False
                self._last_return = now
            log.info("Return edge hit (%s-opposite) – returning control to server", pos)
            self._release_all_keys()
            self._send({"t": "sw", "dir": "to_server"})
            # Park cursor away from the return edge
            if pos == "right":
                self._mouse.position = (ep + 50, ny)
            elif pos == "left":
                self._mouse.position = (self.sw - ep - 50, ny)
            elif pos == "above":
                self._mouse.position = (nx, self.sh - ep - 50)
            else:  # below
                self._mouse.position = (nx, ep + 50)

    def _on_click(self, button_name: str, pressed: bool):
        btn = _parse_button(button_name)
        if btn is None:
            return
        if pressed:
            self._mouse.press(btn)
        else:
            self._mouse.release(btn)

    def _on_scroll(self, dx, dy):
        self._mouse.scroll(dx, dy)

    def _on_key(self, key_str: str, pressed: bool):
        key = _parse_key(key_str)
        if key is None:
            return
        try:
            if pressed:
                self._kbd.press(key)
                self._pressed_keys.add(key)
            else:
                self._kbd.release(key)
                self._pressed_keys.discard(key)
        except Exception as exc:
            log.debug("Key inject failed for %r: %s", key_str, exc)

    def _release_all_keys(self):
        """Libera todas las teclas inyectadas para evitar que queden pegadas."""
        for key in list(self._pressed_keys):
            try:
                self._kbd.release(key)
            except Exception:
                pass
        self._pressed_keys.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send(self, event: dict):
        with self._lock:
            conn = self._conn
        if conn is None:
            return
        try:
            conn.sendall(encode(event))
        except OSError as exc:
            log.warning("Send failed: %s", exc)

    def _build_hotkey_listener(self):
        """Build a GlobalHotKeys listener for the return_hotkey combo."""
        combo = self.cfg.return_hotkey
        # Convert "ctrl+alt+z" → "<ctrl>+<alt>+z" for pynput GlobalHotKeys
        _modifiers = {"ctrl", "alt", "shift", "cmd", "win", "super"}
        parts = [p.strip() for p in combo.lower().split("+")]
        converted = [f"<{p}>" if p in _modifiers else p for p in parts]
        hotkey_str = "+".join(converted)

        def _on_hotkey():
            with self._lock:
                if not self._active:
                    return
                self._active = False
            log.info("Return hotkey (%s) pressed – returning control to server", combo)
            self._release_all_keys()
            cx, cy = self._mouse.position
            self._send({"t": "sw", "dir": "to_server"})
            self._mouse.position = (self.cfg.edge_px + 50, cy)

        # En macOS, GlobalHotKeys requiere permisos de Accessibility.
        # Si no están, no lo iniciamos para evitar bloquear el teclado del sistema.
        if hasattr(keyboard, "GlobalHotKeys"):
            try:
                import subprocess
                result = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to return UI elements enabled'],
                    capture_output=True, text=True, timeout=3
                )
                accessibility_ok = result.stdout.strip() == "true"
            except Exception:
                accessibility_ok = True  # no podemos verificar, intentamos igual

            if not accessibility_ok:
                log.warning(
                    "Sin permisos de Accessibility — hotkey desactivado. "
                    "Agrega esta app en System Settings > Privacy & Security > Accessibility. "
                    "El return-by-edge sigue funcionando."
                )
                return None

        try:
            return keyboard.GlobalHotKeys({hotkey_str: _on_hotkey})
        except Exception as exc:
            log.warning("Could not register hotkey %r: %s", hotkey_str, exc)
            return None


# ------------------------------------------------------------------
# Key / button parsing
# ------------------------------------------------------------------

def _parse_key(k: str):
    """Convert a serialised key name back to a pynput key object."""
    if k.startswith("Key."):
        attr = k[4:]
        return getattr(Key, attr, None)
    if len(k) == 1:
        return k
    return None


def _parse_button(name: str) -> Optional[Button]:
    return {
        "left": Button.left,
        "right": Button.right,
        "middle": Button.middle,
    }.get(name)
