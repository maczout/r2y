"""CLI entry point for r2y.

Usage:
    python cli.py validate examples/rect_beam.json
    python cli.py info examples/rect_beam.json
    python cli.py layers examples/rect_beam.json
    python cli.py material-curves examples/rect_beam.json [--output curves.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from r2y.schema import R2YModel
from r2y.materials.concrete import (
    concrete_compression,
    concrete_tension,
    default_epsilon_c_prime,
    default_tensile_strength,
    elastic_modulus,
)
from r2y.materials.steel import steel_stress
from r2y.section.geometry import total_height, area as section_area
from r2y.section.layers import generate_layers


def _load_model(path: str) -> R2YModel:
    text = Path(path).read_text()
    return R2YModel.model_validate_json(text)


def cmd_validate(args: argparse.Namespace) -> None:
    try:
        _load_model(args.path)
        print("Valid")
    except Exception as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args: argparse.Namespace) -> None:
    model = _load_model(args.path)
    m = model.metadata
    print(f"Description : {m.description}")
    print(f"Units       : {m.units}")
    print(f"Schema      : {m.schema_version}")
    print()

    geom = model.section.geometry
    h = total_height(geom)
    a = section_area(geom)
    print(f"Section height : {h:.1f} mm")
    print(f"Gross area     : {a:.1f} mm²")
    for i, s in enumerate(geom.strips):
        print(f"  Strip {i}: y_top={s.y_top:.1f}, h={s.height:.1f}, w={s.width:.1f}, concrete={s.concrete_id}")
    print()

    for c in model.materials.concrete:
        fc = c.fc_prime
        ft = c.ft if c.ft is not None else default_tensile_strength(fc, m.units)
        ec = elastic_modulus(fc)
        ecp = c.epsilon_c_prime if c.epsilon_c_prime is not None else default_epsilon_c_prime(fc)
        print(f"Concrete '{c.id}': fc'={fc:.1f} MPa, ft={ft:.2f} MPa, Ec={ec:.0f} MPa, εc'={ecp:.4f} mm/m")

    for s in model.materials.steel:
        fu = s.fu if s.fu is not None else 1.5 * s.fy
        print(f"Steel '{s.id}': fy={s.fy:.1f} MPa, E={s.E:.0f} MPa, fu={fu:.1f} MPa")
    print()

    total_as = sum(r.area for r in model.section.reinforcement)
    rho = total_as / a * 100.0 if a > 0 else 0.0
    print(f"Reinforcement layers: {len(model.section.reinforcement)}")
    for r in model.section.reinforcement:
        print(f"  y={r.y:.1f} mm, As={r.area:.1f} mm², steel={r.steel_id}")
    print(f"Total As = {total_as:.1f} mm²,  ρ = {rho:.3f}%")

    if model.section.stirrups:
        st = model.section.stirrups
        print(f"Stirrups: Av/s={st.area_per_spacing:.2f} mm²/mm, steel={st.steel_id}")
    print()

    ld = model.loading
    print(f"Loading: N={ld.axial_load:.1f}, type={ld.load_type}, M/V={ld.moment_to_shear_ratio}, increments={ld.num_increments}")


def cmd_layers(args: argparse.Namespace) -> None:
    model = _load_model(args.path)
    lyrs = generate_layers(model.section, num_layers=args.num_layers)
    print(f"{'#':>4}  {'y_center':>10}  {'thickness':>10}  {'width':>10}  {'rebar_area':>10}  {'concrete_id'}")
    print("-" * 70)
    for i, l in enumerate(lyrs):
        print(
            f"{i:4d}  {l.y_center:10.2f}  {l.thickness:10.2f}  {l.width:10.2f}  {l.rebar_area:10.2f}  {l.concrete_id}"
        )


def cmd_material_curves(args: argparse.Namespace) -> None:
    model = _load_model(args.path)
    num_points = 50
    result: dict = {"concrete": [], "steel": []}

    for c in model.materials.concrete:
        fc = c.fc_prime
        ft = c.ft if c.ft is not None else default_tensile_strength(fc, model.metadata.units)
        ec = elastic_modulus(fc)
        ecp = c.epsilon_c_prime if c.epsilon_c_prime is not None else default_epsilon_c_prime(fc)

        comp_strains = [i * 3.0 * ecp / (num_points - 1) for i in range(num_points)]
        comp_stresses = [concrete_compression(e, 0.0, fc, ecp) for e in comp_strains]

        ten_strains = [i * 5.0 / (num_points - 1) for i in range(num_points)]
        ten_stresses = [concrete_tension(e, ft, ec, c.tension_stiffening) for e in ten_strains]

        result["concrete"].append({
            "id": c.id,
            "fc_prime": fc,
            "ft": ft,
            "Ec": ec,
            "eps_c_prime": ecp,
            "compression": {"strain_mm_m": comp_strains, "stress_MPa": comp_stresses},
            "tension": {"strain_mm_m": ten_strains, "stress_MPa": ten_stresses},
        })

    for s in model.materials.steel:
        fu = s.fu if s.fu is not None else 1.5 * s.fy
        strains = [(i - num_points // 2) * 240.0 / (num_points - 1) for i in range(num_points)]
        stresses = [steel_stress(e, s.fy, s.E, fu, s.epsilon_sh, s.epsilon_u) for e in strains]
        result["steel"].append({
            "id": s.id,
            "fy": s.fy,
            "fu": fu,
            "strains_mm_m": strains,
            "stresses_MPa": stresses,
        })

    json_str = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(json_str)
        print(f"Written to {args.output}")
    else:
        print(json_str)


def main() -> None:
    parser = argparse.ArgumentParser(description="r2y — Response-2000 reimplementation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate a JSON input file")
    p_validate.add_argument("path")
    p_validate.set_defaults(func=cmd_validate)

    p_info = sub.add_parser("info", help="Print section summary")
    p_info.add_argument("path")
    p_info.set_defaults(func=cmd_info)

    p_layers = sub.add_parser("layers", help="Print layer breakdown")
    p_layers.add_argument("path")
    p_layers.add_argument("--num-layers", type=int, default=40)
    p_layers.set_defaults(func=cmd_layers)

    p_curves = sub.add_parser("material-curves", help="Dump material stress-strain curves")
    p_curves.add_argument("path")
    p_curves.add_argument("--output", default=None)
    p_curves.set_defaults(func=cmd_material_curves)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
