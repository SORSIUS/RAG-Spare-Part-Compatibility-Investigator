import json
import sys
from pathlib import Path


def configuration():
    entry = Path(__file__).resolve().parents[1] / "mcp_entry.py"
    return {"mcpServers": {"spare-parts": {"command": sys.executable, "args": ["-X", "utf8", str(entry)]}}}


if __name__ == "__main__":
    print(json.dumps(configuration(), indent=2))
