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
from time import monotonic
from typing import Optional

from pynput import keyboard, mouse
from pynput.mouse import Button

from .config import Config
from .protocol import decode_from_buffer, encode
from .screen import get_screen_rect

log = logging.getLogger(__name__)


class Server:
    def __init__(self, config: Config):
        self.cfg = config
        rect = get_screen_rect()
        self.sx, self.sy = rect[0], rect[1]          # top-left of primary monitor
        self.sw, self.sh = rect[2] - rect[0], rect[3] - rect[1]
        log.info("Screen rect: (%d,%d)-(%d,%d)  size: %dx%d",
                 rect[0], rect[1], rect[2], rect[3], self.sw, self.sh)

        self._mode = "LOCAL"          # "LOCAL" | "REMOTE"
        self._mode_lock = threading.Lock()

        self._conn: Optional[socket.socket] = None
        self._conn_lock = threading.Lock()

        # Cursor pin position (set dynamically on edge trigger)
        self._pin_x = self.sx + self.sw - self.cfg.edge_px
        self._pin_y = self.sy + self.sh // 2

        # Active pynput listeners (swapped on mode change)
        self._monitor_listener: Optional[mouse.Listener] = None
        self._cap_mouse: Optional[mouse.Listener] = None
        self._cap_kbd: Optional[keyboard.Listener] = None

        self._mouse_ctrl = mouse.Controller()
        self._kbd_ctrl = keyboard.Controller()
        self._running = True
        self._last_exit_time: float = 0.0  # monotonic time of last _exit_remote
        self._pressed_keys: set = set()     # keys held while in REMOTE mode

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
            # Send an immediate ping so the client knows the connection is live
            # before the ping_loop's first sleep expires
            try:
                conn.sendall(encode({"t": "ping"}))
            except OSError:
                pass
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
        with self._mode_lock:
            in_remote = self._mode == "REMOTE"
        if in_remote:
            threading.Thread(target=self._exit_remote, daemon=True).start()

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
                # Run in a separate thread so _recv_loop isn't blocked while
                # _exit_remote waits for cap listeners to stop
                threading.Thread(target=self._exit_remote, daemon=True).start()

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
        with self._mode_lock:
            if self._mode == "REMOTE":
                return
        if monotonic() - self._last_exit_time < 1.0:
            return
        with self._conn_lock:
            connected = self._conn is not None
        if connected and self._edge_triggered(x, y):
            self._enter_remote(x, y)

    def _edge_triggered(self, x: int, y: int) -> bool:
        pos = self.cfg.remote_position
        ep = self.cfg.edge_px
        if pos == "right":
            return x >= self.sx + self.sw - ep
        if pos == "left":
            return x <= self.sx + ep
        if pos == "above":
            return y <= self.sy + ep
        if pos == "below":
            return y >= self.sy + self.sh - ep
        return False

    # ------------------------------------------------------------------
    # Mode: REMOTE – suppressing listeners that forward events
    # ------------------------------------------------------------------

    def _enter_remote(self, cursor_x: int, cursor_y: int):
        with self._mode_lock:
            if self._mode == "REMOTE":
                return
            self._mode = "REMOTE"

        log.info("→ REMOTE mode  (remote_position=%s)", self.cfg.remote_position)

        # Pin cursor at the edge that was triggered
        # (monitor listener keeps running — _monitor_on_move ignores events while REMOTE)
        pos = self.cfg.remote_position
        ep = self.cfg.edge_px
        if pos == "right":
            self._pin_x, self._pin_y = self.sx + self.sw - ep, cursor_y
        elif pos == "left":
            self._pin_x, self._pin_y = self.sx + ep, cursor_y
        elif pos == "above":
            self._pin_x, self._pin_y = cursor_x, self.sy + ep
        elif pos == "below":
            self._pin_x, self._pin_y = cursor_x, self.sy + self.sh - ep
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

        # Set cooldown immediately — the monitor checks this before the cursor
        # is parked, so it must be set before any slow stop() calls below.
        self._last_exit_time = monotonic()
        log.info("→ LOCAL mode")

        if self._cap_mouse:
            self._cap_mouse.stop()
            self._cap_mouse = None
        if self._cap_kbd:
            self._cap_kbd.stop()
            self._cap_kbd = None

        # Release any keys that were held while in REMOTE mode so Windows
        # doesn't think they're still pressed after control returns.
        for key in list(self._pressed_keys):
            try:
                self._kbd_ctrl.release(key)
            except Exception:
                pass
        self._pressed_keys.clear()

        # Move cursor away from edge so monitor doesn't re-trigger immediately
        pos = self.cfg.remote_position
        px, py = self._pin_x, self._pin_y
        if pos == "right":
            park = (self.sx + self.sw // 2, py)
        elif pos == "left":
            park = (self.sx + self.sw // 2, py)
        elif pos == "above":
            park = (px, self.sy + self.sh // 2)
        else:  # below
            park = (px, self.sy + self.sh // 2)
        self._mouse_ctrl.position = park
        # monitor listener never stopped — no need to restart it

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
        self._pressed_keys.add(key)
        self._send({"t": "kp", "k": _key_str(key), "p": True})

    def _cap_on_release(self, key):
        self._pressed_keys.discard(key)
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
            with self._mode_lock:
                in_remote = self._mode == "REMOTE"
            if in_remote:
                threading.Thread(target=self._exit_remote, daemon=True).start()


def _key_str(key) -> str:
    try:
        return key.char  # printable character
    except AttributeError:
        return str(key)  # e.g. "Key.space"
