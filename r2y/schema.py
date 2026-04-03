"""Consolidated JSON schema for r2y — the single data contract for input/output.

Uses dataclasses with JSON serialization. Will migrate to Pydantic v2 when
available (the API surface is identical: model_validate_json / model_dump_json
will be added as class methods).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _from_dict(cls, d: dict):
    """Recursively instantiate a dataclass from a dict."""
    import inspect
    hints = cls.__dataclass_fields__
    kwargs = {}
    for fname, fld in hints.items():
        val = d.get(fname, fld.default if fld.default is not fld.default_factory else fld.default_factory())
        if val is None and fld.default is None:
            kwargs[fname] = None
            continue
        # Handle missing with default
        if fname not in d:
            if fld.default is not fld.default_factory:
                kwargs[fname] = fld.default
            else:
                kwargs[fname] = fld.default_factory()
            continue
        ftype = fld.type
        # Resolve string annotations
        if isinstance(ftype, str):
            ftype = _resolve_type(ftype)
        kwargs[fname] = _coerce(ftype, val)
    return cls(**kwargs)


def _resolve_type(type_str: str):
    """Resolve forward-referenced type strings."""
    import sys
    mod = sys.modules[__name__]
    # Strip Optional wrapper
    if type_str.startswith("Optional["):
        inner = type_str[len("Optional["):-1]
        return Optional[_resolve_type(inner)]
    if type_str.startswith("list["):
        inner = type_str[len("list["):-1]
        return list[_resolve_type(inner)]
    return getattr(mod, type_str, str)


def _coerce(ftype, val):
    """Coerce a value into the expected type."""
    if val is None:
        return None

    origin = getattr(ftype, "__origin__", None)

    # list[X]
    if origin is list:
        inner = ftype.__args__[0]
        if hasattr(inner, "__dataclass_fields__") and isinstance(val, list):
            return [_from_dict(inner, v) if isinstance(v, dict) else v for v in val]
        return val

    # Optional[X]
    import typing
    if origin is typing.Union:
        args = [a for a in ftype.__args__ if a is not type(None)]
        if len(args) == 1:
            return _coerce(args[0], val)
        return val

    # Nested dataclass
    if hasattr(ftype, "__dataclass_fields__") and isinstance(val, dict):
        return _from_dict(ftype, val)

    return val


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@dataclass
class Metadata:
    schema_version: str = "0.1.0"
    program: str = "r2y"
    units: str = "SI"  # "SI" or "US"
    description: str = ""


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

@dataclass
class ConcreteModel:
    id: str = ""
    fc_prime: float = 0.0
    ft: Optional[float] = None
    epsilon_c_prime: Optional[float] = None
    aggregate_size: float = 19.0
    tension_stiffening_factor: float = 1.0
    base_curve: str = "popovics"
    compression_softening: str = "vecchio_collins_1986"
    tension_stiffening: str = "bentz_2000"


@dataclass
class SteelModel:
    id: str = ""
    fy: float = 0.0
    E: float = 200000.0
    fu: Optional[float] = None
    epsilon_sh: float = 7.0
    epsilon_u: float = 100.0


@dataclass
class Materials:
    concrete: list[ConcreteModel] = field(default_factory=list)
    steel: list[SteelModel] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

@dataclass
class Strip:
    y_top: float = 0.0
    height: float = 0.0
    width: float = 0.0
    concrete_id: str = ""


@dataclass
class SectionGeometry:
    """Cross-section as a stack of rectangular strips, top to bottom."""
    strips: list[Strip] = field(default_factory=list)


@dataclass
class RebarLayer:
    y: float = 0.0
    area: float = 0.0
    steel_id: str = ""
    count: Optional[int] = None
    bar_diameter: Optional[float] = None


@dataclass
class Stirrups:
    area_per_spacing: float = 0.0
    steel_id: str = ""
    spacing: Optional[float] = None
    leg_area: Optional[float] = None


@dataclass
class Section:
    geometry: SectionGeometry = field(default_factory=SectionGeometry)
    reinforcement: list[RebarLayer] = field(default_factory=list)
    stirrups: Optional[Stirrups] = None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

@dataclass
class Loading:
    axial_load: float = 0.0
    load_type: str = "full_response"  # "sectional" or "full_response"
    moment_to_shear_ratio: Optional[float] = None
    num_increments: int = 100


# ---------------------------------------------------------------------------
# Results (output only — populated by engine)
# ---------------------------------------------------------------------------

@dataclass
class LayerResult:
    y: float = 0.0
    epsilon_x: float = 0.0
    sigma_x: float = 0.0


@dataclass
class LoadStep:
    step: int = 0
    moment: float = 0.0
    shear: float = 0.0
    curvature: float = 0.0
    epsilon_top: float = 0.0
    epsilon_bot: float = 0.0
    layers: list[LayerResult] = field(default_factory=list)


@dataclass
class Results:
    response: list[LoadStep] = field(default_factory=list)
    failure_moment: Optional[float] = None
    failure_shear: Optional[float] = None
    failure_mode: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------

@dataclass
class R2YModel:
    metadata: Metadata = field(default_factory=Metadata)
    materials: Materials = field(default_factory=Materials)
    section: Section = field(default_factory=Section)
    loading: Loading = field(default_factory=Loading)
    results: Optional[Results] = None

    @classmethod
    def model_validate_json(cls, json_str: str) -> "R2YModel":
        """Parse a JSON string into an R2YModel, raising ValueError on errors."""
        d = json.loads(json_str)
        return cls._from_dict(d)

    @classmethod
    def _from_dict(cls, d: dict) -> "R2YModel":
        return _from_dict(cls, d)

    def model_dump(self) -> dict:
        """Serialize to a dict, dropping None values where appropriate."""
        return _clean_dict(asdict(self))

    def model_dump_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.model_dump(), indent=indent)


def _clean_dict(obj):
    """Recursively clean a dict from asdict, keeping None for optional fields."""
    if isinstance(obj, dict):
        return {k: _clean_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_dict(v) for v in obj]
    return obj
