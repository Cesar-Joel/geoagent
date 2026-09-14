"""Entry point de consola `geoagent-backend`."""

from __future__ import annotations

import argparse
import sys

from geoagent import __version__

PROG = "geoagent-backend"


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog=PROG,
        description="Servicio backend de geoagent. Aún no expone subcomandos.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    parser.parse_args(argv)
    parser.print_usage(sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
