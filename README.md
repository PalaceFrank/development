# KVMShare

Share one keyboard and mouse between **Mac and Windows** (or any combo) over your local network — no hardware required.

Move your cursor to the **right edge** of the server screen to hand control to the secondary machine. Move it to the **left edge** on the client to return control.

---

## How it works

```
[Mac / Server]  ──── TCP 24800 ────  [Windows / Client]
  physical KB+mouse                    receives events
  pynput capture                       pynput injection
```

1. **Server** – the machine with the physical keyboard and mouse.  
   Monitors the cursor; when it hits the right screen edge, all input is captured, delta-encoded, and forwarded to the client over TCP.

2. **Client** – the secondary machine.  
   Receives events and injects them via pynput (uses `SendInput` on Windows, `CGEventPost` on macOS). When its cursor reaches the left edge, control returns to the server.

---

## Requirements

- Python 3.10+
- Both machines on the same LAN

```bash
pip install -r requirements.txt
```

### macOS extra (for precise Retina screen size)
```bash
pip install pyobjc-framework-Cocoa
```

### macOS permissions
Go to **System Settings → Privacy & Security → Accessibility** and add your Terminal / Python to the allowed list. Without this, pynput cannot capture or inject events.

### Windows
Run as a regular user — no elevation needed.

---

## Usage

### On the SERVER machine (has keyboard + mouse)
```bash
python run_server.py
# or specify bind address:
python run_server.py --host 0.0.0.0 --port 24800
```

### On the CLIENT machine (secondary)
```bash
python run_client.py --server <SERVER_IP>
# example:
python run_client.py --server 192.168.1.42
```

---

## Configuration (`config.json`)

| Key | Default | Description |
|---|---|---|
| `host` | `"0.0.0.0"` | Server bind address |
| `port` | `24800` | TCP port |
| `edge_px` | `3` | Pixels from right edge that trigger handoff |
| `ping_interval` | `5.0` | Keepalive ping interval (seconds) |

---

## Project structure

```
kvmshare/
  __init__.py     package
  protocol.py     length-prefixed JSON wire format
  screen.py       cross-platform screen size detection
  config.py       config dataclass
  server.py       input capture + TCP server
  client.py       TCP client + input injection
run_server.py     server entry point
run_client.py     client entry point
config.json       default configuration
requirements.txt
```

---

## Known limitations / roadmap

- [ ] Clipboard sharing (copy on one, paste on the other)
- [ ] Multi-monitor support (switch via top/bottom edge too)
- [ ] Encrypted transport (TLS)
- [ ] System tray icon / GUI
- [ ] Auto-discovery via mDNS (no need to type IP)
- [ ] Screen layout configurator (which machine is left/right)
