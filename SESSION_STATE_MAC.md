# KVMShare — Estado del Proyecto (Mac)

**Última actualización:** 2026-04-07
**Rama:** `claude/cross-platform-input-sharing-w4FGj`
**Repo:** `PalaceFrank/development`

---

## Estado general

El cliente Mac está funcional y conectado al servidor Windows (`192.168.1.83:24800`).
Build generado con PyInstaller sobre Python 3.9 (macOS arm64).

---

## Binarios

| Archivo | Descripción |
|---------|-------------|
| `dist/macos/kvmshare-client` | Cliente CLI (máquina secundaria) |
| `dist/macos/kvmshare-server` | Servidor CLI (si el Mac fuera el principal) |
| `dist/macos/kvmshare-gui` | GUI CLI |
| `dist/macos/KVMShare Client.app` | App de doble clic |
| `dist/macos/config.json` | Configuración activa |

**Release GitHub:** v1.0.0 — `kvmshare-macos-v1.0.0.zip` (24 MB)

---

## Cómo correr el cliente

```bash
# Desde source (recomendado para desarrollo):
python3 run_client.py --server 192.168.1.83 --debug

# Desde binario:
./dist/macos/kvmshare-client --server 192.168.1.83
```

**Requisito macOS:** Terminal (o el binario) debe estar en:
> System Settings → Privacy & Security → Accessibility

---

## config.json activo

```json
{
  "host": "0.0.0.0",
  "port": 24800,
  "edge_px": 3,
  "ping_interval": 5.0,
  "return_hotkey": "ctrl+alt+z",
  "remote_position": "right"
}
```

- `remote_position: "right"` → el Mac está a la **derecha** del Windows
- Return edge: borde **izquierdo** del Mac devuelve control a Windows
- Hotkey de emergencia: `Ctrl+Alt+Z`

---

## Fixes aplicados en esta sesión (client.py)

| Fix | Descripción |
|-----|-------------|
| Python 3.9 compat | `X \| None` → `Optional[X]` en type hints |
| TCP keepalive | `SO_KEEPALIVE` + `TCP_KEEPALIVE=10s` a nivel socket |
| Reconexión robusta | `time.sleep(5)` en cierres limpios, no solo en errores |
| Client-side ping loop | `_ping_loop` envía `{"t":"ping"}` cada `ping_interval`s — no depende de pings del servidor |
| Sin recv timeout | `settimeout(None)` — elimina falsos timeouts en modo LOCAL |
| Teclas pegadas | `_pressed_keys` + `_release_all_keys()` al perder control |
| Cooldown return edge | 1s de cooldown evita re-triggers por cursor oscilante |
| Race condition `_active` | Protegido con `self._lock` en `_dispatch` y `_on_hotkey` |
| GlobalHotKeys permisos | Verifica Accessibility con `osascript` antes de registrar hotkey |

---

## Problema pendiente (requiere fix en Windows)

- El servidor crashea o cae al recibir `{"t":"sw","dir":"to_server"}` — Francisco reporta "se cae todo" al volver del Mac al PC
- El `ping_loop` del servidor no parece correr después de `_exit_remote()` — las conexiones no recibían pings del servidor (resuelto desde el Mac con client-side pings)
- Investigar `_handle_incoming` y `_exit_remote()` en `server.py`

---

## Próxima sesión

- Interfaz gráfica (tray icon, conexión visual, indicador de máquina activa)
- Soporte para más de 2 máquinas (múltiples clientes)

---

## Arquitectura

```
kvmshare/
├── client.py      # Recibe eventos TCP, los inyecta en Mac via pynput
├── server.py      # Captura input en la máquina principal, envía por TCP
├── config.py      # Configuración (ping_interval, edge_px, etc.)
├── protocol.py    # Encode/decode de eventos JSON
└── screen.py      # Obtiene resolución de pantalla

run_client.py      # Launcher del cliente
run_server.py      # Launcher del servidor
run_gui.py         # Launcher de la GUI
build.py           # Build cross-platform con PyInstaller
```
