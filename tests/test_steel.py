"""Tests for steel constitutive model."""

import pytest

from r2y.materials.steel import steel_stress, steel_tangent

FY = 400.0
E = 200000.0
FU = 600.0
EPS_SH = 7.0
EPS_U = 100.0


def _ss(strain: float) -> float:
    return steel_stress(strain, FY, E, FU, EPS_SH, EPS_U)


class TestSteelStress:
    def test_zero_strain(self):
        assert _ss(0.0) == 0.0

    def test_yield_point(self):
        eps_y = FY / E * 1000.0  # 2.0 mm/m
        f = _ss(eps_y)
        assert abs(f - FY) < 0.1

    def test_end_of_plateau(self):
        f = _ss(EPS_SH)
        assert abs(f - FY) < 0.1

    def test_ultimate(self):
        f = _ss(EPS_U)
        assert abs(f - FU) < 0.1

    def test_rupture(self):
        f = _ss(EPS_U + 10.0)
        assert f == 0.0

    def test_symmetry_negative(self):
        eps_y = FY / E * 1000.0
        f_pos = _ss(eps_y)
        f_neg = _ss(-eps_y)
        assert abs(f_pos + f_neg) < 0.01

    def test_negative_yield(self):
        f = _ss(-EPS_SH)
        assert abs(f - (-FY)) < 0.1

    def test_negative_ultimate(self):
        f = _ss(-EPS_U)
        assert abs(f - (-FU)) < 0.1

    def test_negative_rupture(self):
        assert _ss(-EPS_U - 10.0) == 0.0


class TestSteelTangent:
    def test_elastic_tangent(self):
        # In the elastic region, tangent = E/1000 (MPa per mm/m)
        t = steel_tangent(0.5, FY, E, FU, EPS_SH, EPS_U)
        expected = E / 1000.0  # 200 MPa per mm/m
        assert abs(t - expected) / expected < 0.01

    def test_plateau_tangent(self):
        t = steel_tangent(5.0, FY, E, FU, EPS_SH, EPS_U)
        assert abs(t) < 1.0  # essentially zero
