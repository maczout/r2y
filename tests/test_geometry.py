"""Tests for cross-section geometry."""

import pytest

from r2y.section.geometry import (
    rectangular_section,
    tee_section,
    total_height,
    width_at_depth,
    area,
)


class TestRectangular:
    def test_area(self):
        g = rectangular_section(300.0, 600.0)
        assert abs(area(g) - 300.0 * 600.0) < 0.01

    def test_height(self):
        g = rectangular_section(300.0, 600.0)
        assert abs(total_height(g) - 600.0) < 0.01

    def test_width_at_depth(self):
        g = rectangular_section(300.0, 600.0)
        assert abs(width_at_depth(g, 100.0) - 300.0) < 0.01
        assert abs(width_at_depth(g, 500.0) - 300.0) < 0.01


class TestTeeBeam:
    def test_area(self):
        g = tee_section(1000.0, 150.0, 300.0, 850.0)
        expected = 1000.0 * 150.0 + 300.0 * 850.0
        assert abs(area(g) - expected) < 0.01

    def test_height(self):
        g = tee_section(1000.0, 150.0, 300.0, 850.0)
        assert abs(total_height(g) - 1000.0) < 0.01

    def test_width_in_flange(self):
        g = tee_section(1000.0, 150.0, 300.0, 850.0)
        assert abs(width_at_depth(g, 75.0) - 1000.0) < 0.01

    def test_width_in_web(self):
        g = tee_section(1000.0, 150.0, 300.0, 850.0)
        assert abs(width_at_depth(g, 500.0) - 300.0) < 0.01

    def test_width_outside(self):
        g = tee_section(1000.0, 150.0, 300.0, 850.0)
        assert width_at_depth(g, -10.0) == 0.0
        assert width_at_depth(g, 1100.0) == 0.0
