"""Dispatcher: no args → GUI, subcommands → CLI, --version, --help."""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) == 1:
        from microProfiler.gui.app import main as gui_main
        gui_main()
        return 0

    if sys.argv[1] == "--version":
        from importlib.metadata import version
        print(f"microProfiler {version('microProfiler')}")
        return 0

    if sys.argv[1] in ("run", "convert"):
        from microProfiler.cli import main as cli_main
        return cli_main(sys.argv[1:])

    if sys.argv[1] == "--help":
        from microProfiler.cli import build_parser
        build_parser().print_help()
        return 0

    print(f"Unknown argument: {sys.argv[1]}", file=sys.stderr)
    print("Usage: microprofiler [run | convert | --version | --help]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
