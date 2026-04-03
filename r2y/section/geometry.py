"""Cross-section geometry helpers for r2y."""

from __future__ import annotations

from r2y.schema import SectionGeometry, Strip


def rectangular_section(
    width: float, height: float, concrete_id: str = "concrete_1"
) -> SectionGeometry:
    """Create a single rectangular strip."""
    return SectionGeometry(
        strips=[Strip(y_top=0.0, height=height, width=width, concrete_id=concrete_id)]
    )


def tee_section(
    flange_width: float,
    flange_depth: float,
    web_width: float,
    web_depth: float,
    concrete_id: str = "concrete_1",
) -> SectionGeometry:
    """Create a T-beam: flange on top, web below."""
    return SectionGeometry(
        strips=[
            Strip(y_top=0.0, height=flange_depth, width=flange_width, concrete_id=concrete_id),
            Strip(y_top=flange_depth, height=web_depth, width=web_width, concrete_id=concrete_id),
        ]
    )


def total_height(geometry: SectionGeometry) -> float:
    """Total section height."""
    if not geometry.strips:
        return 0.0
    last = geometry.strips[-1]
    return last.y_top + last.height


def width_at_depth(geometry: SectionGeometry, y: float) -> float:
    """Section width at depth y from top.  Returns 0 if outside section."""
    for strip in geometry.strips:
        if strip.y_top <= y < strip.y_top + strip.height:
            return strip.width
    # Check exact bottom edge
    if geometry.strips:
        last = geometry.strips[-1]
        if abs(y - (last.y_top + last.height)) < 1e-9:
            return last.width
    return 0.0


def area(geometry: SectionGeometry) -> float:
    """Gross cross-sectional area."""
    return sum(s.height * s.width for s in geometry.strips)
