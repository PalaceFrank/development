"""Configuration dataclass loaded from config.json."""

import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # Network
    host: str = "0.0.0.0"
    port: int = 24800

    # How many pixels from the right edge trigger the switch (server-side)
    edge_px: int = 3

    # Seconds between keepalive pings
    ping_interval: float = 5.0

    # Hotkey to force-return control to server (client-side edge + this combo)
    return_hotkey: str = "ctrl+alt+z"

    # Where the client screen is relative to the server screen
    # Values: "right" | "left" | "above" | "below"
    remote_position: str = "right"

    @classmethod
    def from_file(cls, path: str = "config.json") -> "Config":
        if not os.path.exists(path):
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: str = "config.json") -> None:
        import dataclasses
        with open(path, "w") as f:
            json.dump(dataclasses.asdict(self), f, indent=2)
