#!/usr/bin/env python3
"""
KVMShare — Build script
Genera los binarios para la plataforma actual.

Windows → dist/windows/  con .exe para server, client y GUI
macOS   → dist/macos/    con binario CLI para server/client y .app para GUI y client

Uso:
    pip install pyinstaller
    python build.py
    python build.py --target server   # solo el server
    python build.py --target client   # solo el client
    python build.py --target gui      # solo la GUI
"""

import argparse
import os
import shutil
import subprocess
import sys

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_BASE = os.path.join(ROOT, "dist")

PLATFORM = sys.platform  # "win32" | "darwin" | "linux"
PLATFORM_DIR = {
    "win32":  os.path.join(DIST_BASE, "windows"),
    "darwin": os.path.join(DIST_BASE, "macos"),
}.get(PLATFORM, os.path.join(DIST_BASE, "linux"))

# ── Targets ──────────────────────────────────────────────────────────────────
TARGETS = {
    "server": "kvmshare-server.spec",
    "client": "kvmshare-client.spec",
    "gui":    "kvmshare-gui.spec",
}

# On Windows we typically only distribute server+GUI (this machine has the KB/mouse).
# On macOS we typically only distribute client. But we build all for flexibility.
DEFAULT_TARGETS = list(TARGETS.keys())


# ── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd: list[str], **kwargs):
    print(f"\n>>> {' '.join(cmd)}\n")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[ERROR] PyInstaller no está instalado. Instálalo con:")
        print("        pip install pyinstaller")
        sys.exit(1)


def build_target(name: str):
    spec = os.path.join(ROOT, TARGETS[name])
    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--distpath={PLATFORM_DIR}",
            f"--workpath={os.path.join(ROOT, 'build', PLATFORM, name)}",
            spec,
        ],
        cwd=ROOT,
    )


def copy_config():
    """Place a default config.json next to each binary so they can find it."""
    src = os.path.join(ROOT, "config.json")
    if not os.path.exists(src):
        return
    dst = os.path.join(PLATFORM_DIR, "config.json")
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        print(f"[+] config.json -> {dst}")
    else:
        print(f"[i] config.json ya existe en {dst}, no se sobreescribe")


def print_summary(targets: list[str]):
    print("\n" + "=" * 60)
    print(f"  Build completado - {PLATFORM}")
    print(f"  Salida: {PLATFORM_DIR}")
    print("=" * 60)
    for name in targets:
        if PLATFORM == "win32":
            exe = os.path.join(PLATFORM_DIR, f"kvmshare-{name}.exe")
        else:
            exe = os.path.join(PLATFORM_DIR, f"kvmshare-{name}")
        exists = "[OK]" if os.path.exists(exe) else "[--]"
        print(f"  {exists}  {exe}")
    print()
    print("  Copia la carpeta completa a cada maquina.")
    if PLATFORM == "win32":
        print("  Windows -> ejecutar kvmshare-server.exe")
        print("  Windows -> ejecutar kvmshare-gui.exe  (para configurar)")
    else:
        print("  macOS -> ejecutar kvmshare-client --server <IP_DEL_SERVER>")
        print("  macOS -> KVMShare Client.app (doble clic)")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="KVMShare build script")
    parser.add_argument(
        "--target",
        choices=list(TARGETS.keys()),
        default=None,
        help="Construir solo este target (default: todos)",
    )
    args = parser.parse_args()

    check_pyinstaller()
    os.makedirs(PLATFORM_DIR, exist_ok=True)

    targets = [args.target] if args.target else DEFAULT_TARGETS

    for name in targets:
        print(f"\n{'-'*60}")
        print(f"  Construyendo: {name}  [{PLATFORM}]")
        print(f"{'-'*60}")
        build_target(name)

    copy_config()
    print_summary(targets)


if __name__ == "__main__":
    main()
