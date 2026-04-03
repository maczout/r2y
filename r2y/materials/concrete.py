"""Concrete constitutive models for r2y.

Sign convention: strains and stresses are positive in tension, negative in
compression internally. Functions in this module work with *magnitudes*
(positive values) — the caller handles sign flipping.

Units: strain in mm/m, stress in MPa (SI mode).
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Default properties
# ---------------------------------------------------------------------------

def default_tensile_strength(fc_prime: float, units: str = "SI") -> float:
    """Tensile strength ft from cylinder strength fc'."""
    if units == "SI":
        return 0.33 * math.sqrt(fc_prime)
    return 4.0 * math.sqrt(fc_prime)


def elastic_modulus(fc_prime: float) -> float:
    """Ec = 3320*sqrt(fc') + 6900  [MPa]."""
    return 3320.0 * math.sqrt(fc_prime) + 6900.0


def default_epsilon_c_prime(fc_prime: float) -> float:
    """Strain at peak stress (mm/m, positive value).

    n  = 0.8 + fc'/17
    Ec = 3320*sqrt(fc') + 6900
    εc' = (fc'/Ec) * (n/(n-1))
    """
    n = 0.8 + fc_prime / 17.0
    ec = elastic_modulus(fc_prime)
    # fc'/Ec is dimensionless strain; multiply by 1000 to get mm/m
    return (fc_prime / ec) * (n / (n - 1.0)) * 1000.0


# ---------------------------------------------------------------------------
# Popovics/Thorenfeldt/Collins base curve (compression)
# ---------------------------------------------------------------------------

def popovics_base(eps2: float, fc_prime: float, eps_c_prime: float) -> float:
    """Popovics base curve (Eq 5-1).

    Args:
        eps2: compressive strain magnitude (positive, mm/m)
        fc_prime: cylinder strength (MPa, positive)
        eps_c_prime: strain at peak stress (mm/m, positive)

    Returns:
        Compressive stress magnitude (positive, MPa).
    """
    if eps2 <= 0.0 or eps_c_prime <= 0.0:
        return 0.0
    n = 0.8 + fc_prime / 17.0
    ratio = eps2 / eps_c_prime
    k = 1.0
    if ratio > 1.0:
        k = 0.67 + fc_prime / 62.0
    denom = n - 1.0 + ratio ** (n * k)
    if denom <= 0.0:
        return 0.0
    return fc_prime * ratio * n / denom


# ---------------------------------------------------------------------------
# Compression with Vecchio-Collins 1986 softening
# ---------------------------------------------------------------------------

def compression_softening_beta(eps1: float) -> float:
    """Vecchio-Collins 1986 softening factor beta.

    Args:
        eps1: principal tensile strain (positive, mm/m).
    """
    eps1 = max(eps1, 0.0)
    beta = 1.0 / (0.8 + 170.0 * eps1)
    return min(beta, 1.0)


def concrete_compression(
    eps2: float, eps1: float, fc_prime: float, eps_c_prime: float
) -> float:
    """Softened Popovics compression curve.

    Args:
        eps2: principal compressive strain magnitude (positive, mm/m)
        eps1: principal tensile strain (positive, mm/m)
        fc_prime: cylinder strength (MPa, positive)
        eps_c_prime: strain at peak stress (mm/m, positive)

    Returns:
        Compressive stress magnitude (positive, MPa).
    """
    beta = compression_softening_beta(eps1)
    f2max = beta * fc_prime

    if eps2 <= 0.0 or eps_c_prime <= 0.0:
        return 0.0

    n = 0.8 + fc_prime / 17.0
    ratio = eps2 / eps_c_prime
    k = 1.0
    if ratio > 1.0:
        k = 0.67 + fc_prime / 62.0
    denom = n - 1.0 + ratio ** (n * k)
    if denom <= 0.0:
        return 0.0
    f2 = f2max * ratio * n / denom
    return max(f2, 0.0)


# ---------------------------------------------------------------------------
# Compression tangent stiffness (numerical)
# ---------------------------------------------------------------------------

def concrete_compression_tangent(
    eps2: float,
    eps1: float,
    fc_prime: float,
    eps_c_prime: float,
    delta: float = 1e-6,
) -> float:
    """df2/d(eps2) via central difference."""
    f_plus = concrete_compression(eps2 + delta, eps1, fc_prime, eps_c_prime)
    f_minus = concrete_compression(max(eps2 - delta, 0.0), eps1, fc_prime, eps_c_prime)
    actual_delta = (eps2 + delta) - max(eps2 - delta, 0.0)
    if actual_delta == 0.0:
        return 0.0
    return (f_plus - f_minus) / actual_delta


# ---------------------------------------------------------------------------
# Concrete in tension
# ---------------------------------------------------------------------------

def concrete_tension(
    eps1: float,
    ft: float,
    ec: float,
    tension_model: str = "collins_mitchell_1987",
    tension_stiffening_factor: float = 1.0,
) -> float:
    """Concrete tensile stress.

    Args:
        eps1: tensile strain (positive, mm/m)
        ft: tensile strength (MPa)
        ec: elastic modulus (MPa)
        tension_model: "collins_mitchell_1987" or "bentz_2000"
        tension_stiffening_factor: multiplier on post-crack tension (0 to 1)

    Returns:
        Tensile stress (positive, MPa).
    """
    if eps1 <= 0.0:
        return 0.0

    eps_cr = ft / ec  # cracking strain in mm/m
    if eps1 <= eps_cr:
        return ec * eps1

    # Post-cracking tension stiffening
    if tension_model == "bentz_2000":
        # TODO: Full Bentz 2000 model requires crack spacing from layer system.
        # Falling back to Collins-Mitchell 1987 for now.
        f1 = ft / (1.0 + math.sqrt(500.0 * eps1))
    else:
        # Collins-Mitchell 1987
        f1 = ft / (1.0 + math.sqrt(500.0 * eps1))

    return f1 * tension_stiffening_factor


# ---------------------------------------------------------------------------
# Shear on crack limit (Walraven equation)
# ---------------------------------------------------------------------------

def effective_aggregate_size(aggregate_size: float, fc_prime: float) -> float:
    """Reduce aggregate size for high-strength concrete."""
    if fc_prime >= 80.0:
        return 0.0
    if fc_prime >= 60.0:
        return aggregate_size * (80.0 - fc_prime) / 20.0
    return aggregate_size


def vci_max(
    fc_prime: float, crack_width: float, aggregate_size: float
) -> float:
    """Maximum shear stress on a crack (Walraven equation).

    Args:
        fc_prime: cylinder strength (MPa)
        crack_width: w in mm
        aggregate_size: max aggregate size in mm

    Returns:
        vci_max in MPa.
    """
    a_eff = effective_aggregate_size(aggregate_size, fc_prime)
    denom = 0.31 + 24.0 * crack_width / (a_eff + 16.0)
    return 0.18 * math.sqrt(fc_prime) / denom
