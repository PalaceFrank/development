# KVMShare — Estado del proyecto

> Última actualización: 2026-04-07

---

## ¿Qué funciona hoy?

El sistema está **operativo y estable**. Probado en sesión real Windows ↔ Mac:

- El cursor llega al borde derecho de Windows → control pasa al Mac
- El cursor llega al borde izquierdo del Mac → control regresa a Windows
- `Ctrl+Alt+Z` en el Mac fuerza el regreso (hotkey de emergencia)
- Reconexión automática si se interrumpe la red
- Teclas sueltas al volver (no quedan keys "pegadas" en ninguno de los dos equipos)

### Binarios listos

Disponibles en [GitHub Releases v1.0.0](https://github.com/PalaceFrank/development/releases/tag/v1.0.0):

| Archivo | Plataforma | Uso |
|---|---|---|
| `kvmshare-server.exe` | Windows | Máquina con el teclado/mouse físico |
| `kvmshare-client.exe` | Windows (no usar) | Solo para build |
| `kvmshare-gui.exe` | Windows | Configurar posición del Mac |
| `KVMShare-macOS.zip` | macOS | Cliente que recibe el control |

---

## Arquitectura actual

```
Windows (servidor)                    Mac (cliente)
─────────────────                     ──────────────
kvmshare-server.exe                   kvmshare-client
  │                                     │
  ├─ monitor_listener (always on)       ├─ recv_loop  ← recibe mv/kp/mc/ms
  │   └─ detecta borde → REMOTE        ├─ ping_loop  ← envía pings c/5s
  │                                     └─ GlobalHotKeys (ctrl+alt+z)
  ├─ cap_mouse + cap_kbd (REMOTE)
  │   └─ suppress=True, fwd eventos
  │
  └─ TCP :24800
```

**Config activa** (`dist/windows/config.json`):
```json
{
  "edge_px": 20,
  "ping_interval": 5.0,
  "return_hotkey": "ctrl+alt+z",
  "remote_position": "right"
}
```

---

## Bugs corregidos (sesión 2026-04-07)

| Bug | Fix |
|---|---|
| Teclas pegadas al volver | `_pressed_keys` set + `release()` en `_exit_remote` |
| Monitor moría tras primer switch | Monitor listener nunca se detiene; ignora eventos en REMOTE via mode check |
| Deadlock en `_exit_remote` | Todos los call sites usan `threading.Thread` |
| Cooldown seteado tarde | `_last_exit_time` se setea como primera acción, antes de `stop()` |
| Re-trigger inmediato al volver | Cooldown subido de 300ms a 1s |
| Sin ping inmediato al conectar | Servidor manda ping al aceptar la conexión |
| Teclado Mac se bloqueaba | `GlobalHotKeys` verifica permisos Accessibility antes de registrar |
| Teclas inyectadas pegadas en Mac | Mismo fix `_pressed_keys` en `client.py` |

---

## Lo que sigue — GUI de bandeja del sistema

### Objetivo

Reemplazar la dependencia de la terminal por un ícono en la bandeja del sistema (system tray) que muestre el estado y permita control rápido sin abrir ventanas.

### Comportamiento esperado

```
[ícono en bandeja]
  Estado: ● Conectado — Mac a la derecha
  ─────────────────────────────
  ○ Desconectar
  ○ Configuración...
  ─────────────────────────────
  ○ Salir
```

- **Ícono dinámico:** color/forma distinta según estado (LOCAL = gris, REMOTE = verde)
- **Tooltip:** `KVMShare — Conectado / Esperando cliente`
- **Arranque silencioso:** al doble-click en el `.exe`, va directo a bandeja sin mostrar ventana
- **Configuración:** abre la GUI tkinter existente (`kvmshare/gui.py`) para cambiar la posición del Mac

### Stack recomendado

```
pystray      → ícono en bandeja (Windows + macOS)
Pillow       → generar el ícono dinámicamente (círculo de color)
threading    → el server/client corren en background thread
```

### Archivos a crear / modificar

| Archivo | Cambio |
|---|---|
| `kvmshare/tray.py` | Nuevo — clase `TrayApp` que wrappea `pystray` |
| `run_tray.py` | Nuevo — entry point: arranca server + tray |
| `kvmshare-tray.spec` | Nuevo — spec de PyInstaller para el binario tray |
| `build.py` | Agregar build del tray a la lista |
| `requirements.txt` | Agregar `pystray>=0.19` y `Pillow>=10.0` |

### API mínima de `TrayApp`

```python
class TrayApp:
    def __init__(self, server: Server): ...
    def run(self): ...                  # bloquea — corre el loop de la bandeja
    def set_state(self, state: str): ...  # "local" | "remote" | "disconnected"
```

### Íconos sugeridos (generados con Pillow, sin archivos externos)

```python
def _make_icon(color: str) -> Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=color)
    return img

ICONS = {
    "local":        _make_icon("#888888"),  # gris  — esperando
    "remote":       _make_icon("#00cc44"),  # verde — Mac tiene control
    "disconnected": _make_icon("#cc2200"),  # rojo  — sin cliente
}
```

### Integración con el servidor

En lugar de correr `server.run()` directamente (bloquea), se corre en un thread:

```python
server = Server(config)
tray   = TrayApp(server)

# El server notifica al tray cuando cambia de modo
server.on_mode_change = tray.set_state

t = threading.Thread(target=server.run, daemon=True)
t.start()
tray.run()  # bloquea hasta que el usuario cierra
```

Para esto, `server.py` necesita el hook `on_mode_change` (callback opcional).

---

## Dependencias actuales

```
# requirements.txt
pynput>=1.7
keyboard>=0.13

# requirements-dev.txt
pyinstaller>=6.0
```

Agregar para el tray:
```
pystray>=0.19
Pillow>=10.0
```

---

## Cómo correr en desarrollo (sin buildear)

```bash
# Windows — servidor
cd D:\develop\development
python run_server.py

# Mac — cliente
cd ~/Documents/DEV/KVMShare
python run_client.py --server <IP_WINDOWS>

# GUI de configuración (Windows)
python run_gui.py
```
