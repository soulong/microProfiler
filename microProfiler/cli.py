"""Command-line interface for the microProfiler pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pydantic import BaseModel

from microProfiler.config import PipelineConfig, load_config
from microProfiler.logging_utils import set_default_logging_level, setup_logging
from microProfiler.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with ``run`` and ``convert`` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="microProfiler",
        description="Microscopy image preprocessing, segmentation, and profiling pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Enable DEBUG-level logging (verbose output)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──────────────────────────────────────────────────────────────
    run_parser = sub.add_parser(
        "run", help="Run the full analysis pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    run_parser.add_argument("input_dir", type=Path, help="Path to raw measurement directory")
    run_parser.add_argument("--config", "-c", type=Path, default=None, help="YAML config file")
    run_parser.add_argument("--output", "-o", type=Path, default=None, help="Output directory")
    run_parser.add_argument("--format", choices=["operetta", "mica"], default="operetta",
                            help="Vendor format of input data")
    run_parser.add_argument(
        "--convert-resize", type=float, default=None,
        help="Resize scale factor applied during conversion write",
    )
    run_parser.add_argument(
        "--resize", type=float, default=None,
        help="Standalone resize scale factor (after conversion)",
    )
    run_parser.add_argument(
        "--output-name", type=str, default=None,
        help="Converter output subdirectory name (default: image)",
    )
    run_parser.add_argument(
        "--delete-original", action="store_true", default=False,
        help="Delete original vendor files after conversion (default: preserve)",
    )
    run_parser.add_argument(
        "--basic", type=str, default=None,
        choices=["fit", "transform", "fit-transform"],
        help="BaSiC correction mode",
    )
    run_parser.add_argument(
        "--z-projection", type=str, default=None,
        choices=["max", "mean", "min"],
        help="Z-projection method",
    )
    run_parser.add_argument(
        "--tile", type=int, nargs=2, default=None,
        metavar=("W", "H"), help="Tile width and height",
    )
    run_parser.add_argument(
        "--segment", type=str, default=None,
        help="Object name for segmentation (enables segmentation)",
    )
    run_parser.add_argument(
        "--segment-channels", type=str, nargs="+", default=None,
        help="Channel(s) for segmentation C1",
    )
    run_parser.add_argument(
        "--profile-image", action="store_true", default=False,
        help="Enable image-level profiling",
    )
    run_parser.add_argument(
        "--profile-object", type=str, default=None,
        help="Mask name for object-level profiling",
    )
    run_parser.add_argument("--log-file", type=Path, default=None, help="Log output to file")
    run_parser.add_argument(
        "--db", type=str, default="results.db",
        help="Output SQLite database name",
    )

    # ── convert ─────────────────────────────────────────────────────────
    conv_parser = sub.add_parser(
        "convert", help="Convert vendor format to unified naming",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    conv_parser.add_argument("input_dir", type=Path, help="Path to raw measurement directory")
    conv_parser.add_argument("--format", choices=["operetta", "mica"], required=True,
                             help="Vendor format of input data")
    conv_parser.add_argument(
        "--output-name", type=str, default=None,
        help="Output subdirectory name (default: image)",
    )
    conv_parser.add_argument(
        "--convert-resize", type=float, default=None,
        help="Resize scale factor (applied during conversion)",
    )
    conv_parser.add_argument(
        "--delete-original", action="store_true", default=False,
        help="Delete original vendor files after conversion (default: preserve)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv : list of str or None
        Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (``0`` on success, ``1`` on error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if getattr(args, "debug", False) else logging.INFO
    set_default_logging_level(log_level)
    log = setup_logging(
        level=log_level,
        log_file=args.log_file if hasattr(args, "log_file") else None,
    )
    log.debug("Debug logging enabled")

    if args.command == "convert":
        from microProfiler.preprocessing.converter import convert_measurement

        conv_resize = args.convert_resize if args.convert_resize is not None else 1.0
        delete_original = getattr(args, "delete_original", False)
        ds = convert_measurement(
            input_dir=args.input_dir,
            vendor_format=args.format,
            resize_factor=conv_resize,
            output_name=args.output_name if args.output_name else "image",
            delete_original=delete_original,
        )
        log.info("Converted %d files", len(ds))
        return 0

    if args.command == "run":
        if args.config:
            cfg = load_config(args.config)
        else:
            cfg = PipelineConfig(input_dir=args.input_dir, format=args.format)

        if args.output:
            cfg.output_dir = args.output

        # ── Conversion config ───────────────────────────────────────────
        conv = cfg.convert.model_dump() if cfg.convert else {}
        if args.output_name:
            conv["output_name"] = args.output_name
        if args.convert_resize is not None:
            conv["resize_factor"] = args.convert_resize
        if getattr(args, "delete_original", False):
            conv["delete_original"] = True
        if conv:
            cfg.convert = conv

        # ── Standalone resize config ────────────────────────────────────
        if args.resize is not None:
            cfg.resize = {"scale_factor": args.resize}

        # ── Basic correction config ─────────────────────────────────────
        if args.basic:
            cfg.basic_correction = {"mode": args.basic}

        # ── Z-projection config ─────────────────────────────────────────
        if args.z_projection:
            cfg.z_projection = {"method": args.z_projection}

        # ── Tile config ─────────────────────────────────────────────────
        if args.tile:
            cfg.tile = {"tile_width": args.tile[0], "tile_height": args.tile[1]}

        # ── Segmentation config ─────────────────────────────────────────
        if args.segment:
            seg = cfg.segmentation
            if isinstance(seg, BaseModel):
                seg = seg.model_dump()
            else:
                seg = seg or {}
            seg["object_name"] = args.segment
            if args.segment_channels:
                seg["chan1"] = args.segment_channels
            cfg.segmentation = seg

        # ── Profiling config ────────────────────────────────────────────
        if args.profile_image or args.profile_object:
            prof = cfg.profiling
            if isinstance(prof, BaseModel):
                prof = prof.model_dump()
            else:
                prof = prof or {}
            if args.profile_image:
                prof["image_channels"] = None
            if args.profile_object:
                prof["object_mask_name"] = args.profile_object
            cfg.profiling = prof

        run_pipeline(cfg, db_name=args.db, log_file=args.log_file)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
