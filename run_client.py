#!/usr/bin/env python3
"""
KVMShare – Client launcher
Usage:
    python run_client.py --server 192.168.1.10 [--port 24800] [--config config.json]
"""

import argparse
import logging
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")

from kvmshare.config import Config
from kvmshare.client import Client


def main():
    parser = argparse.ArgumentParser(description="KVMShare client (secondary machine)")
    parser.add_argument("--server", required=True, help="Server IP address")
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
    if args.port:
        cfg.port = args.port

    print(f"""
  ██╗  ██╗██╗   ██╗███╗   ███╗███████╗██╗  ██╗ █████╗ ██████╗ ███████╗
  ██║ ██╔╝██║   ██║████╗ ████║██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝
  █████╔╝ ██║   ██║██╔████╔██║███████╗███████║███████║██████╔╝█████╗
  ██╔═██╗ ╚██╗ ██╔╝██║╚██╔╝██║╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝
  ██║  ██╗ ╚████╔╝ ██║ ╚═╝ ██║███████║██║  ██║██║  ██║██║  ██║███████╗
  ╚═╝  ╚═╝  ╚═══╝  ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝

  CLIENT  |  Move cursor to the LEFT EDGE to return control to server
  Server  :  {args.server}:{cfg.port}
  """)

    client = Client(args.server, cfg)
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
