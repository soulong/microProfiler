from __future__ import annotations


import pytest

from microProfiler.cli import build_parser, main


class TestBuildParser:
    def test_parser_has_convert_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["convert", "/data", "--format", "operetta"])
        assert args.command == "convert"
        assert args.format == "operetta"

    def test_parser_has_run_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["run", "/data"])
        assert args.command == "run"

    def test_run_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["run", "/data"])
        assert args.format == "operetta"
        assert args.db == "results.db"
        assert args.profile_image is False
        assert args.profile_object is None

    def test_convert_resize(self):
        parser = build_parser()
        args = parser.parse_args(["convert", "/data", "--format", "operetta", "--convert-resize", "0.5"])
        assert args.convert_resize == 0.5

    def test_convert_output_name(self):
        parser = build_parser()
        args = parser.parse_args(["convert", "/data", "--format", "mica", "--output-name", "out"])
        assert args.output_name == "out"

    def test_run_all_flags(self):
        parser = build_parser()
        args = parser.parse_args([
            "run", "/data", "--format", "mica",
            "--convert-resize", "0.5",
            "--resize", "0.5",
            "--basic", "fit-transform",
            "--z-projection", "max",
            "--tile", "512", "512",
            "--segment", "nuclei",
            "--segment-channels", "ch1", "ch2",
            "--profile-image",
            "--profile-object", "cell",
            "--db", "out.db",
        ])
        assert args.format == "mica"
        assert args.convert_resize == 0.5
        assert args.resize == 0.5
        assert args.basic == "fit-transform"
        assert args.z_projection == "max"
        assert args.tile == [512, 512]
        assert args.segment == "nuclei"
        assert args.segment_channels == ["ch1", "ch2"]
        assert args.profile_image is True
        assert args.profile_object == "cell"
        assert args.db == "out.db"


class TestMain:
    def test_convert_no_format_raises(self):
        with pytest.raises(SystemExit):
            main(["convert", "/data"])

    def test_convert_operetta_copies_files(self, operetta_test_dir, temp_dir):
        # Copy test data to temp dir to avoid modifying original
        import shutil
        temp_input = temp_dir / "input"
        shutil.copytree(str(operetta_test_dir), str(temp_input))
        exit_code = main(["convert", str(temp_input), "--format", "operetta",
                          "--output-name", "unified", "--convert-resize", "1.0"])
        assert exit_code == 0
        converted = temp_input / "unified"
        tiffs = list(converted.glob("*.tiff"))
        assert len(tiffs) > 0

    def test_profile_object_without_profile_image_pipeline_runs(self, operetta_test_dir, temp_dir):
        import shutil
        temp_input = temp_dir / "input"
        shutil.copytree(str(operetta_test_dir), str(temp_input))
        exit_code = main(["run", str(temp_input), "--profile-object", "cell",
                          "--output-name", "prof_test", "--db", str(temp_dir / "out.db")])
        # The CLI bug was TypeError. Now it should complete (exit 0).
        # Pipeline may still fail at runtime (no segmentation), but CLI won't crash.
        assert exit_code == 0
