"""
KVMShare – Server
=================
The machine with the physical keyboard and mouse runs this.

Modes
-----
LOCAL   Normal operation. A non-suppressing mouse listener watches for the
        cursor reaching the right edge of the screen.
REMOTE  The cursor has crossed the edge. All mouse + keyboard events are
        suppressed locally, delta-encoded, and forwarded to the connected
        client over TCP.  When the client sends {"t":"sw","dir":"to_server"}
        the server returns to LOCAL mode.
"""

import logging
import socket
import sys
import threading
import time

from pynput import keyboard, mouse
from pynput.mouse import Button

from .config import Config
from .protocol import decode_from_buffer, encode
from .screen import get_screen_size

log = logging.getLogger(__name__)


class Server:
    def __init__(self, config: Config):
        self.cfg = config
        self.sw, self.sh = get_screen_size()
        log.info("Screen: %dx%d", self.sw, self.sh)

        self._mode = "LOCAL"          # "LOCAL" | "REMOTE"
        self._mode_lock = threading.Lock()

        self._conn: socket.socket | None = None
        self._conn_lock = threading.Lock()

        # Cursor pin position (right edge centre)
        self._pin_x = self.sw - self.cfg.edge_px
        self._pin_y = self.sh // 2

        # Active pynput listeners (swapped on mode change)
        self._monitor_listener: mouse.Listener | None = None
        self._cap_mouse: mouse.Listener | None = None
        self._cap_kbd: keyboard.Listener | None = None

        self._mouse_ctrl = mouse.Controller()
        self._running = True

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self):
        self._start_monitor()
        self._accept_loop()

    # ------------------------------------------------------------------
    # TCP
    # ------------------------------------------------------------------

    def _accept_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.cfg.host, self.cfg.port))
        srv.listen(1)
        log.info("Listening on %s:%d  (waiting for client to connect…)",
                 self.cfg.host, self.cfg.port)
        while self._running:
            try:
                conn, addr = srv.accept()
            except OSError:
                break
            log.info("Client connected from %s", addr)
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self._conn_lock:
                self._conn = conn
            threading.Thread(
                target=self._recv_loop, args=(conn,), daemon=True
            ).start()
            threading.Thread(
                target=self._ping_loop, args=(conn,), daemon=True
            ).start()

    def _recv_loop(self, conn: socket.socket):
        buf = bytearray()
        while True:
            try:
                chunk = conn.recv(4096)
            except OSError:
                chunk = b""
            if not chunk:
                break
            buf.extend(chunk)
            while True:
                event, buf = decode_from_buffer(buf)
                if event is None:
                    break
                self._handle_incoming(event)

        log.info("Client disconnected")
        with self._conn_lock:
            if self._conn is conn:
                self._conn = None
        if self._mode == "REMOTE":
            self._exit_remote()

    def _ping_loop(self, conn: socket.socket):
        while True:
            time.sleep(self.cfg.ping_interval)
            with self._conn_lock:
                if self._conn is not conn:
                    break
                try:
                    conn.sendall(encode({"t": "ping"}))
                except OSError:
                    break

    def _handle_incoming(self, event: dict):
        t = event.get("t")
        if t == "sw" and event.get("dir") == "to_server":
            if self._mode == "REMOTE":
                self._exit_remote()

    # ------------------------------------------------------------------
    # Mode: LOCAL  – lightweight edge-detection listener (no suppress)
    # ------------------------------------------------------------------

    def _start_monitor(self):
        self._monitor_listener = mouse.Listener(
            on_move=self._monitor_on_move,
            suppress=False,
        )
        self._monitor_listener.start()

    def _monitor_on_move(self, x, y):
        with self._conn_lock:
            connected = self._conn is not None
        if connected and x >= self.sw - self.cfg.edge_px:
            self._enter_remote(y)

    # ------------------------------------------------------------------
    # Mode: REMOTE – suppressing listeners that forward events
    # ------------------------------------------------------------------

    def _enter_remote(self, cursor_y: int):
        with self._mode_lock:
            if self._mode == "REMOTE":
                return
            self._mode = "REMOTE"

        log.info("→ REMOTE mode")

        # Stop the monitor
        if self._monitor_listener:
            self._monitor_listener.stop()
            self._monitor_listener = None

        # Pin cursor
        self._pin_y = cursor_y
        self._mouse_ctrl.position = (self._pin_x, self._pin_y)

        # Start capturing listeners (suppress=True eats all local events)
        self._cap_mouse = mouse.Listener(
            on_move=self._cap_on_move,
            on_click=self._cap_on_click,
            on_scroll=self._cap_on_scroll,
            suppress=True,
        )
        self._cap_kbd = keyboard.Listener(
            on_press=self._cap_on_press,
            on_release=self._cap_on_release,
            suppress=True,
        )
        self._cap_mouse.start()
        self._cap_kbd.start()

    def _exit_remote(self):
        with self._mode_lock:
            if self._mode == "LOCAL":
                return
            self._mode = "LOCAL"

        log.info("→ LOCAL mode")

        if self._cap_mouse:
            self._cap_mouse.stop()
            self._cap_mouse = None
        if self._cap_kbd:
            self._cap_kbd.stop()
            self._cap_kbd = None

        # Move cursor away from edge so monitor doesn't re-trigger immediately
        self._mouse_ctrl.position = (self.sw - 100, self._pin_y)
        self._start_monitor()

    # ------------------------------------------------------------------
    # Capture callbacks (REMOTE mode)
    # ------------------------------------------------------------------

    def _cap_on_move(self, x, y):
        dx = x - self._pin_x
        dy = y - self._pin_y
        if dx or dy:
            self._send({"t": "mv", "dx": dx, "dy": dy})
            # Warp back to pin so cursor doesn't escape
            self._mouse_ctrl.position = (self._pin_x, self._pin_y)

    def _cap_on_click(self, x, y, button: Button, pressed: bool):
        self._send({"t": "mc", "b": button.name, "p": pressed})

    def _cap_on_scroll(self, x, y, dx, dy):
        self._send({"t": "ms", "dx": dx, "dy": dy})

    def _cap_on_press(self, key):
        self._send({"t": "kp", "k": _key_str(key), "p": True})

    def _cap_on_release(self, key):
        self._send({"t": "kp", "k": _key_str(key), "p": False})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send(self, event: dict):
        with self._conn_lock:
            conn = self._conn
        if conn is None:
            return
        try:
            conn.sendall(encode(event))
        except OSError:
            log.warning("Send failed – dropping connection")
            with self._conn_lock:
                self._conn = None
            if self._mode == "REMOTE":
                self._exit_remote()


def _key_str(key) -> str:
    try:
        return key.char  # printable character
    except AttributeError:
        return str(key)  # e.g. "Key.space"
