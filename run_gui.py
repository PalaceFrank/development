#!/usr/bin/env python3
"""
KVMShare — GUI launcher
Abre la ventana de configuración de disposición de pantallas.

Usage:
    python run_gui.py [--config config.json]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kvmshare.gui import LayoutGUI

_BASE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                            else os.path.abspath(__file__))
_DEFAULT_CONFIG = os.path.join(_BASE_DIR, "config.json")


def main():
    parser = argparse.ArgumentParser(description="KVMShare — configuración de pantallas")
    parser.add_argument("--config", default=_DEFAULT_CONFIG, help="Ruta al config.json")
    args = parser.parse_args()

    gui = LayoutGUI(config_path=args.config)
    gui.run()


if __name__ == "__main__":
    main()
