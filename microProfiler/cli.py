"""Command-line interface for the microProfiler pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel

from microProfiler.config import PipelineConfig, load_config
from microProfiler.logging_utils import setup_logging
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
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──────────────────────────────────────────────────────────────
    run_parser = sub.add_parser("run", help="Run the full analysis pipeline")
    run_parser.add_argument("input_dir", type=Path, help="Path to raw measurement directory")
    run_parser.add_argument("--config", "-c", type=Path, default=None, help="YAML config file")
    run_parser.add_argument("--output", "-o", type=Path, default=None, help="Output directory")
    run_parser.add_argument("--format", choices=["operetta", "mica"], default="operetta")
    run_parser.add_argument(
        "--resize", type=float, default=None,
        help="Resize scale factor (applied during conversion)",
    )
    run_parser.add_argument(
        "--output-name", type=str, default=None,
        help="Converter output subdirectory name",
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
        "--profile-image", action="store_true",
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
    conv_parser = sub.add_parser("convert", help="Convert vendor format to unified naming")
    conv_parser.add_argument("input_dir", type=Path, help="Path to raw measurement directory")
    conv_parser.add_argument("--format", choices=["operetta", "mica"], required=True)
    conv_parser.add_argument(
        "--output-name", type=str, default=None,
        help="Output subdirectory name (default: unified)",
    )
    conv_parser.add_argument(
        "--resize", type=float, default=None,
        help="Resize scale factor (applied during conversion)",
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

    log = setup_logging(log_file=args.log_file if hasattr(args, "log_file") else None)

    if args.command == "convert":
        from microProfiler.preprocessing.converter import convert_measurement

        result = convert_measurement(
            input_dir=args.input_dir,
            vendor_format=args.format,
            resize_factor=args.resize if args.resize is not None else 1.0,
            output_name=args.output_name if args.output_name else "unified",
        )
        log.info("Converted %d files", len(result))
        return 0

    if args.command == "run":
        if args.config:
            cfg = load_config(args.config)
        else:
            cfg = PipelineConfig(input_dir=args.input_dir, format=args.format)

        if args.output:
            cfg.output_dir = args.output
        if args.resize is not None:
            cfg.convert = {"resize_factor": args.resize}
        if args.output_name:
            conv = cfg.convert.model_dump() if cfg.convert else {}
            conv["output_name"] = args.output_name
            cfg.convert = conv
        if args.basic:
            cfg.basic_correction = {"mode": args.basic}
        if args.z_projection:
            cfg.z_projection = {"method": args.z_projection}
        if args.tile:
            cfg.tile = {"tile_width": args.tile[0], "tile_height": args.tile[1]}
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
        if args.profile_image or args.profile_object:
            prof = cfg.profiling
            if isinstance(prof, BaseModel):
                prof = prof.model_dump()
            else:
                prof = prof or {}
            if args.profile_image:
                prof["image_channels"] = []
            cfg.profiling = prof
        if args.profile_object:
            cfg.profiling["object_mask_name"] = args.profile_object

        run_pipeline(cfg, db_name=args.db, log_file=args.log_file)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
