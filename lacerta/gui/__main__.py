"""python -m lacerta.gui"""

from __future__ import annotations

import argparse

from lacerta.core.envload import load_dotenv
from lacerta.gui.server import serve


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Lacerta thin local GUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
