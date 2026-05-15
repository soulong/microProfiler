from __future__ import annotations

import re

import numpy as np
import pytest

from microProfiler.preprocessing.converter import (
    OPERETTA_PATTERN,
    _build_unified_name,
    _find_mica_root,
    _resize_if_needed,
    convert_measurement,
)


class TestOperettaPattern:
    def test_match_standard(self):
        m = OPERETTA_PATTERN.match("r02c02f01p01-ch1sk1fk1fl1.tiff")
        assert m is not None
        assert m.group("row") == "02"
        assert m.group("column") == "02"
        assert m.group("field") == "01"
        assert m.group("stack") == "01"
        assert m.group("channel") == "1"
        assert m.group("timepoint") == "1"

    def test_match_field64(self):
        m = OPERETTA_PATTERN.match("r04c02f64p01-ch2sk1fk1fl1.tiff")
        assert m is not None
        assert m.group("field") == "64"
        assert m.group("channel") == "2"

    def test_no_match_wrong_ext(self):
        m = OPERETTA_PATTERN.match("r02c02f01p01-ch1sk1fk1fl1.jpg")
        assert m is None

    def test_no_match_garbage(self):
        m = OPERETTA_PATTERN.match("garbage.txt")
        assert m is None


class TestBuildUnifiedName:
    def test_basic(self):
        name = _build_unified_name("B2", field=1, stack=1, timepoint=1, channel=1)
        assert name == "B2_f1_z1_t1_ch1.tiff"

    def test_multi_digit(self):
        name = _build_unified_name("A11", field=64, stack=3, timepoint=2, channel=12)
        assert name == "A11_f64_z3_t2_ch12.tiff"


class TestResizeIfNeeded:
    def test_no_resize(self):
        img = np.ones((10, 10), dtype=np.uint16)
        result = _resize_if_needed(img, 1.0)
        assert result.shape == (10, 10)
        assert np.array_equal(result, img)

    def test_resize_half(self):
        img = np.ones((10, 10), dtype=np.uint16)
        result = _resize_if_needed(img, 0.5)
        assert result.shape == (5, 5)
        assert result.dtype == np.uint16

    def test_resize_double(self):
        img = np.ones((10, 10), dtype=np.uint16)
        result = _resize_if_needed(img, 2.0)
        assert result.shape == (20, 20)


class TestConvertMeasurement:
    def test_convert_operetta_end_to_end(self, operetta_test_dir, temp_dir):
        out = temp_dir / "unified"
        results = convert_measurement(
            input_dir=operetta_test_dir,
            vendor_format="operetta",
            root_dir=temp_dir,
        )
        assert len(results) > 0
        assert out.exists()
        assert all(p.exists() for p in results)

    def test_converted_filenames_format(self, operetta_test_dir, temp_dir):
        results = convert_measurement(
            input_dir=operetta_test_dir,
            vendor_format="operetta",
            root_dir=temp_dir,
            output_name="test_converted",
        )
        pattern = re.compile(r"[A-Z]\d+_f\d+_z\d+_t\d+_ch\d+\.tiff")
        for p in results:
            assert pattern.match(p.name), f"Bad filename: {p.name}"

    def test_operetta_well_parsing(self, operetta_test_dir, temp_dir):
        results = convert_measurement(
            input_dir=operetta_test_dir,
            vendor_format="operetta",
            root_dir=temp_dir,
        )
        names = [p.name for p in results]
        # r02c02 -> B2, r04c02 -> D2
        assert any("B2" in n for n in names)
        assert any("D2" in n for n in names)

    def test_convert_operetta_with_resize(self, operetta_test_dir, temp_dir):
        results = convert_measurement(
            input_dir=operetta_test_dir,
            vendor_format="operetta",
            root_dir=temp_dir,
            resize_factor=0.5,
            output_name="resized",
        )
        assert len(results) > 0
        for p in results:
            assert p.exists()

    def test_unknown_format_raises(self, temp_dir):
        with pytest.raises(ValueError, match="Unknown vendor format"):
            convert_measurement(temp_dir, vendor_format="invalid")

    def test_empty_dir_raises(self, temp_dir):
        with pytest.raises((NotADirectoryError, RuntimeError)):
            convert_measurement(temp_dir, vendor_format="operetta")


class TestMica:
    def test_find_root(self, mica_test_dir):
        root = _find_mica_root(mica_test_dir)
        assert root == mica_test_dir

    def test_find_root_from_child(self, mica_test_dir):
        child = mica_test_dir / "B"
        root = _find_mica_root(child)
        assert root == mica_test_dir
