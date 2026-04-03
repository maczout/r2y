"""Layer generation for numerical integration through a cross-section."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from r2y.schema import Section
from r2y.section.geometry import width_at_depth, total_height


@dataclass
class Layer:
    y_center: float
    thickness: float
    width: float
    concrete_id: str
    rebar_area: float = 0.0
    rebar_steel_id: Optional[str] = None
    rebar_bar_diameter: Optional[float] = None
    is_stirrup_layer: bool = False


def generate_layers(section: Section, num_layers: int = 40) -> list[Layer]:
    """Generate layers through the section depth.

    Layers are distributed proportionally through each strip.  At each rebar
    depth a layer centroid is forced to coincide with the bar location.
    """
    geometry = section.geometry
    h = total_height(geometry)
    if h <= 0.0 or num_layers < 1:
        return []

    # Collect rebar y positions for snapping
    rebar_ys: dict[float, list[int]] = {}
    for idx, rb in enumerate(section.reinforcement):
        rebar_ys.setdefault(rb.y, []).append(idx)

    # Allocate layers per strip proportionally
    layers: list[Layer] = []
    for strip in geometry.strips:
        strip_bottom = strip.y_top + strip.height
        # Number of layers for this strip (at least 1)
        n_strip = max(1, round(num_layers * strip.height / h))
        layer_h = strip.height / n_strip

        for i in range(n_strip):
            y_c = strip.y_top + layer_h * (i + 0.5)
            layers.append(
                Layer(
                    y_center=y_c,
                    thickness=layer_h,
                    width=strip.width,
                    concrete_id=strip.concrete_id,
                )
            )

    # Snap rebar into nearest layer or split if needed
    for rb in section.reinforcement:
        best_idx = _closest_layer_index(layers, rb.y)
        if best_idx is not None:
            layers[best_idx].rebar_area += rb.area
            layers[best_idx].rebar_steel_id = rb.steel_id
            if rb.bar_diameter is not None:
                layers[best_idx].rebar_bar_diameter = rb.bar_diameter

    # TODO: Dynamic subdivision — R2K subdivides layers when crack fronts
    # pass through them during analysis.  Implement in Session 2/3.

    return layers


def _closest_layer_index(layers: list[Layer], y: float) -> Optional[int]:
    """Return index of the layer whose centroid is closest to y."""
    if not layers:
        return None
    best = 0
    best_dist = abs(layers[0].y_center - y)
    for i in range(1, len(layers)):
        d = abs(layers[i].y_center - y)
        if d < best_dist:
            best_dist = d
            best = i
    return best
