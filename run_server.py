#!/usr/bin/env python3
"""
KVMShare – Server launcher
Usage:
    python run_server.py [--host 0.0.0.0] [--port 24800] [--config config.json]
"""

import argparse
import logging
import sys

# Make the package importable from repo root
sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")

from kvmshare.config import Config
from kvmshare.server import Server


def main():
    parser = argparse.ArgumentParser(description="KVMShare server (has the keyboard & mouse)")
    parser.add_argument("--host", default=None, help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="TCP port (default: 24800)")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = Config.from_file(args.config)
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port

    print(f"""
  ██╗  ██╗██╗   ██╗███╗   ███╗███████╗██╗  ██╗ █████╗ ██████╗ ███████╗
  ██║ ██╔╝██║   ██║████╗ ████║██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝
  █████╔╝ ██║   ██║██╔████╔██║███████╗███████║███████║██████╔╝█████╗
  ██╔═██╗ ╚██╗ ██╔╝██║╚██╔╝██║╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝
  ██║  ██╗ ╚████╔╝ ██║ ╚═╝ ██║███████║██║  ██║██║  ██║██║  ██║███████╗
  ╚═╝  ╚═╝  ╚═══╝  ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝

  SERVER  |  Move cursor to the RIGHT EDGE to hand off control
  """)

    server = Server(cfg)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
