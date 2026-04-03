"""Steel constitutive model for r2y.

The model is bilinear to yield, flat through the yield plateau, then
quadratic strain hardening to ultimate.  Symmetric in tension/compression.

Units: strain in mm/m, stress in MPa (SI mode).
Note: 1 mm/m = 0.001 dimensionless strain.
"""

from __future__ import annotations


def steel_stress(
    strain: float,
    fy: float,
    E: float,
    fu: float,
    epsilon_sh: float,
    epsilon_u: float,
) -> float:
    """Steel stress from strain.

    Args:
        strain: strain in mm/m (positive = tension)
        fy: yield strength (MPa)
        E: elastic modulus (MPa)
        fu: ultimate strength (MPa)
        epsilon_sh: strain at start of hardening (mm/m)
        epsilon_u: strain at ultimate stress (mm/m)

    Returns:
        Stress in MPa.
    """
    eps_abs = abs(strain)
    sign = 1.0 if strain >= 0.0 else -1.0
    eps_y = fy / E * 1000.0  # yield strain in mm/m

    if eps_abs <= eps_y:
        # stress = E * dimensionless_strain = E * (strain_mm_m / 1000)
        return E * strain / 1000.0

    if eps_abs <= epsilon_sh:
        return fy * sign

    if eps_abs <= epsilon_u:
        p = (eps_abs - epsilon_sh) / (epsilon_u - epsilon_sh)
        fs = fy + (fu - fy) * (2.0 * p - p * p)
        return fs * sign

    # Ruptured
    return 0.0


def steel_tangent(
    strain: float,
    fy: float,
    E: float,
    fu: float,
    epsilon_sh: float,
    epsilon_u: float,
    delta: float = 1e-6,
) -> float:
    """dfs/dε (MPa per mm/m) via central difference."""
    f_plus = steel_stress(strain + delta, fy, E, fu, epsilon_sh, epsilon_u)
    f_minus = steel_stress(strain - delta, fy, E, fu, epsilon_sh, epsilon_u)
    return (f_plus - f_minus) / (2.0 * delta)
