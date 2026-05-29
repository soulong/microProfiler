"""Dispatcher: no args → GUI, subcommands → CLI, --version, --help."""
from __future__ import annotations

import logging
import sys

from microProfiler.logging_utils import _ensure_std_streams


def main() -> int:
    """Dispatch to GUI or CLI based on command-line arguments.

    No arguments launches the PySide6 desktop GUI.  ``--version`` prints
    the installed version, ``--help`` shows the CLI help screen.  ``run``
    or ``convert`` subcommand delegates to the CLI.

    Returns
    -------
    int
        Exit code (0 for success, 1 for unknown arguments).
    """
    _ensure_std_streams()
    debug_mode = "--debug" in sys.argv

    if "--version" in sys.argv:
        from importlib.metadata import version
        print(f"microProfiler {version('microProfiler')}")
        return 0

    if "--help" in sys.argv and "run" not in sys.argv and "convert" not in sys.argv:
        from microProfiler.cli import build_parser
        build_parser().print_help()
        return 0

    if len(sys.argv) == 1 or (len(sys.argv) == 2 and debug_mode):
        if debug_mode:
            from microProfiler.logging_utils import set_default_logging_level
            set_default_logging_level(logging.DEBUG)
        from microProfiler.gui.app import main as gui_main
        gui_main()
        return 0

    if "run" in sys.argv or "convert" in sys.argv:
        from microProfiler.cli import main as cli_main
        return cli_main(sys.argv[1:])

    print(f"Unknown argument: {sys.argv[1]}", file=sys.stderr)
    print("Usage: microprofiler [run | convert | --version | --help]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
