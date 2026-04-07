#!/usr/bin/env python3
"""
KVMShare – Client launcher
Usage:
    python run_client.py --server 192.168.1.10 [--port 24800] [--config config.json]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kvmshare.config import Config
from kvmshare.client import Client

_BASE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                            else os.path.abspath(__file__))
_DEFAULT_CONFIG = os.path.join(_BASE_DIR, "config.json")


def main():
    parser = argparse.ArgumentParser(description="KVMShare client (secondary machine)")
    parser.add_argument("--server", required=True, help="Server IP address")
    parser.add_argument("--port", type=int, default=None, help="TCP port (default: 24800)")
    parser.add_argument("--config", default=_DEFAULT_CONFIG, help="Path to config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = Config.from_file(args.config)
    if args.port:
        cfg.port = args.port

    print(f"""
  +-----------------------------------------+
  |  KVMShare CLIENT                        |
  |  Move cursor to the edge to return      |
  |  Server: {args.server}:{cfg.port:<20}|
  +-----------------------------------------+
  """)

    client = Client(args.server, cfg)
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
