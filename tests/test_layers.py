"""Tests for layer generation."""

import pytest

from r2y.schema import (
    Section,
    SectionGeometry,
    Strip,
    RebarLayer,
    Stirrups,
)
from r2y.section.layers import generate_layers
from r2y.section.geometry import area as section_area


def _rect_section() -> Section:
    return Section(
        geometry=SectionGeometry(
            strips=[Strip(y_top=0.0, height=600.0, width=300.0, concrete_id="concrete_1")]
        ),
        reinforcement=[
            RebarLayer(y=550.0, area=1500.0, steel_id="rebar_1", bar_diameter=25.2),
        ],
    )


def _tee_section() -> Section:
    return Section(
        geometry=SectionGeometry(
            strips=[
                Strip(y_top=0.0, height=150.0, width=1000.0, concrete_id="concrete_1"),
                Strip(y_top=150.0, height=850.0, width=300.0, concrete_id="concrete_1"),
            ]
        ),
        reinforcement=[
            RebarLayer(y=900.0, area=3600.0, steel_id="rebar_1"),
        ],
    )


class TestRectLayers:
    def test_layer_count(self):
        layers = generate_layers(_rect_section(), num_layers=40)
        assert len(layers) == 40

    def test_spans_depth(self):
        layers = generate_layers(_rect_section(), num_layers=40)
        assert layers[0].y_center < 20.0
        assert layers[-1].y_center > 580.0

    def test_area_sum(self):
        sec = _rect_section()
        layers = generate_layers(sec, num_layers=40)
        total = sum(l.thickness * l.width for l in layers)
        expected = section_area(sec.geometry)
        assert abs(total - expected) / expected < 0.01

    def test_rebar_placed(self):
        layers = generate_layers(_rect_section(), num_layers=40)
        rebar_layers = [l for l in layers if l.rebar_area > 0]
        assert len(rebar_layers) >= 1
        assert abs(sum(l.rebar_area for l in rebar_layers) - 1500.0) < 0.01
        # Rebar should be near y=550
        for l in rebar_layers:
            assert abs(l.y_center - 550.0) < 20.0


class TestTeeLayers:
    def test_flange_width(self):
        layers = generate_layers(_tee_section(), num_layers=40)
        flange_layers = [l for l in layers if l.y_center < 150.0]
        for l in flange_layers:
            assert abs(l.width - 1000.0) < 0.01

    def test_web_width(self):
        layers = generate_layers(_tee_section(), num_layers=40)
        web_layers = [l for l in layers if l.y_center > 150.0]
        for l in web_layers:
            assert abs(l.width - 300.0) < 0.01

    def test_area_sum(self):
        sec = _tee_section()
        layers = generate_layers(sec, num_layers=40)
        total = sum(l.thickness * l.width for l in layers)
        expected = section_area(sec.geometry)
        assert abs(total - expected) / expected < 0.01
