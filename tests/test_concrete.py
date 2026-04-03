"""Tests for concrete constitutive models."""

import math
import pytest

from r2y.materials.concrete import (
    concrete_compression,
    concrete_compression_tangent,
    concrete_tension,
    compression_softening_beta,
    default_epsilon_c_prime,
    default_tensile_strength,
    elastic_modulus,
    popovics_base,
    vci_max,
    effective_aggregate_size,
)


FC = 35.0  # MPa


class TestDefaults:
    def test_elastic_modulus(self):
        ec = elastic_modulus(FC)
        expected = 3320.0 * math.sqrt(35.0) + 6900.0
        assert abs(ec - expected) < 1.0

    def test_tensile_strength_si(self):
        ft = default_tensile_strength(FC, "SI")
        expected = 0.33 * math.sqrt(35.0)
        assert abs(ft - expected) < 0.01

    def test_tensile_strength_us(self):
        ft = default_tensile_strength(4000.0, "US")
        expected = 4.0 * math.sqrt(4000.0)
        assert abs(ft - expected) < 0.1

    def test_n_parameter(self):
        n = 0.8 + FC / 17.0
        assert abs(n - 2.859) < 0.01

    def test_epsilon_c_prime(self):
        ecp = default_epsilon_c_prime(FC)
        assert ecp > 0.0
        # Should be around 1.8-2.2 mm/m for 35 MPa
        assert 1.5 < ecp < 3.0


class TestPopovicsBase:
    def test_zero_strain(self):
        ecp = default_epsilon_c_prime(FC)
        assert popovics_base(0.0, FC, ecp) == 0.0

    def test_peak_stress(self):
        ecp = default_epsilon_c_prime(FC)
        f_peak = popovics_base(ecp, FC, ecp)
        assert abs(f_peak - FC) < 0.1

    def test_post_peak_descending(self):
        ecp = default_epsilon_c_prime(FC)
        f_peak = popovics_base(ecp, FC, ecp)
        f_post = popovics_base(2.0 * ecp, FC, ecp)
        assert f_post < f_peak


class TestCompressionSoftening:
    def test_no_softening_at_zero_tension(self):
        beta = compression_softening_beta(0.0)
        assert abs(beta - 1.0) < 0.01  # 1/0.8 = 1.25 capped at 1.0

    def test_significant_softening(self):
        beta = compression_softening_beta(2.0)
        expected = 1.0 / (0.8 + 170.0 * 2.0)
        assert abs(beta - expected) < 0.0001
        assert beta < 0.01

    def test_softened_compression(self):
        ecp = default_epsilon_c_prime(FC)
        f_unsoftened = concrete_compression(ecp, 0.0, FC, ecp)
        f_softened = concrete_compression(ecp, 2.0, FC, ecp)
        assert f_softened < f_unsoftened * 0.1


class TestTension:
    def test_pre_crack_linear(self):
        ft = default_tensile_strength(FC)
        ec = elastic_modulus(FC)
        eps_cr = ft / ec
        eps_test = eps_cr * 0.5
        f = concrete_tension(eps_test, ft, ec)
        expected = ec * eps_test
        assert abs(f - expected) < 0.01

    def test_at_cracking(self):
        ft = default_tensile_strength(FC)
        ec = elastic_modulus(FC)
        eps_cr = ft / ec
        f = concrete_tension(eps_cr, ft, ec)
        assert abs(f - ft) < 0.01

    def test_post_crack_decay(self):
        ft = default_tensile_strength(FC)
        ec = elastic_modulus(FC)
        eps_cr = ft / ec
        f_crack = concrete_tension(eps_cr, ft, ec)
        f_post = concrete_tension(1.0, ft, ec)
        expected = ft / (1.0 + math.sqrt(500.0 * 1.0))
        assert abs(f_post - expected) < 0.01
        assert f_post < f_crack

    def test_negative_strain_returns_zero(self):
        ft = default_tensile_strength(FC)
        ec = elastic_modulus(FC)
        assert concrete_tension(-1.0, ft, ec) == 0.0


class TestTangent:
    def test_tangent_at_origin(self):
        ecp = default_epsilon_c_prime(FC)
        # Near zero, tangent df/d(eps2) in MPa/(mm/m) should approximate Ec/1000
        # since eps2 is in mm/m and 1 mm/m = 0.001 dimensionless strain
        t = concrete_compression_tangent(0.01, 0.0, FC, ecp)
        ec_per_mm_m = elastic_modulus(FC) / 1000.0  # ≈26.5 MPa/(mm/m)
        assert abs(t - ec_per_mm_m) / ec_per_mm_m < 0.2


class TestVciMax:
    def test_basic(self):
        v = vci_max(35.0, 0.1, 19.0)
        assert v > 0.0

    def test_high_strength_aggregate(self):
        a_eff = effective_aggregate_size(19.0, 90.0)
        assert a_eff == 0.0
        a_eff2 = effective_aggregate_size(19.0, 70.0)
        assert abs(a_eff2 - 19.0 * 10.0 / 20.0) < 0.01
