# KVMShare - Build en Mac (contexto para Claude)

## Situacion
Este repo tiene el software KVMShare listo para buildear en Mac.
- **Windows server** ya esta corriendo en `192.168.1.83:24800`
- Tarea: generar el binario Mac del cliente y conectarlo al server Windows

## Pasos a ejecutar

### 1. Instalar dependencias
```bash
pip install pynput pyinstaller
```

### 2. Buildear el cliente Mac
```bash
cd /ruta/donde/clonaste/development
python build.py
```
Genera: `dist/macos/kvmshare-client`

### 3. Permisos macOS (IMPORTANTE)
Antes de correr el cliente:
- **System Settings > Privacy & Security > Accessibility**
- Agregar Terminal (o la app desde donde corras el binario)
- Sin esto pynput no puede inyectar eventos de mouse/teclado

### 4. Ejecutar el cliente
```bash
./dist/macos/kvmshare-client --server 192.168.1.83
```

### 5. Probar
- El cursor llega al borde configurado en Windows -> control pasa al Mac
- Ctrl+Alt+Z -> devuelve el control a Windows (hotkey de emergencia)

## Arquitectura
- `kvmshare/server.py` - captura input en Windows, envia por TCP
- `kvmshare/client.py` - recibe eventos, los inyecta en Mac via pynput
- `config.json` - configuracion (puerto 24800, remote_position: "right")
- `build.py` - build cross-platform, detecta el OS automaticamente

## Rama git
`claude/cross-platform-input-sharing-w4FGj`

## Si algo falla
- Error de Accessibility: revisar permisos (paso 3)
- `Connection refused`: verificar que `kvmshare-server.exe` este corriendo en Windows
- Build falla: verificar que pyinstaller este instalado (`pip install pyinstaller`)
