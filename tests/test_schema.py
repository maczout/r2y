"""Tests for the consolidated JSON schema."""

import json
from pathlib import Path

from r2y.schema import R2YModel


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestRectBeam:
    def test_load_valid(self):
        text = (EXAMPLES_DIR / "rect_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        assert model.metadata.program == "r2y"
        assert model.materials.concrete[0].fc_prime == 35.0

    def test_round_trip(self):
        text = (EXAMPLES_DIR / "rect_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        dumped = model.model_dump_json()
        model2 = R2YModel.model_validate_json(dumped)
        assert model == model2

    def test_results_absent(self):
        text = (EXAMPLES_DIR / "rect_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        assert model.results is None


class TestTeeBeam:
    def test_load_valid(self):
        text = (EXAMPLES_DIR / "tee_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        assert len(model.section.geometry.strips) == 2

    def test_round_trip(self):
        text = (EXAMPLES_DIR / "tee_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        dumped = model.model_dump_json()
        model2 = R2YModel.model_validate_json(dumped)
        assert model == model2


class TestValidationErrors:
    def test_missing_required_field(self):
        # With dataclasses, missing top-level keys will use defaults
        # but malformed JSON should raise
        try:
            R2YModel.model_validate_json("not valid json")
            assert False, "Should have raised"
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    def test_bad_json_structure(self):
        try:
            R2YModel.model_validate_json('"just a string"')
            assert False, "Should have raised"
        except (TypeError, AttributeError, ValueError):
            pass


class TestDefaults:
    def test_ft_defaults_to_none(self):
        text = (EXAMPLES_DIR / "rect_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        # ft is None in input — auto-computation happens at usage time
        assert model.materials.concrete[0].ft is None

    def test_fu_defaults_to_none(self):
        text = (EXAMPLES_DIR / "rect_beam.json").read_text()
        model = R2YModel.model_validate_json(text)
        assert model.materials.steel[0].fu is None
