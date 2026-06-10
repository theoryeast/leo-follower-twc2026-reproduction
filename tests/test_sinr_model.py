from __future__ import annotations

import unittest

import numpy as np

from src.leo_follower_model import SystemParams, db_to_linear
from src.sinr_model import (
    _ground_branch_bandwidths,
    access_coverage_curve,
    conditional_interference_moments,
    end_to_end_coverage_curve,
    estimate_boundary_follower_interference_fraction,
    run_sinr_validation,
    scenario_params,
    semi_analytical_leader_metrics,
    simulate_sinr_samples,
)


class SinrModelTests(unittest.TestCase):
    def test_validation_gate(self) -> None:
        result = run_sinr_validation()
        self.assertTrue(result["all_acceptance_checks_pass"], result)

    def test_fixed_ground_bandwidth_under_orthogonal_resources(self) -> None:
        p = SystemParams(n_followers=10)
        bw_l, bw_f = _ground_branch_bandwidths(p, scenario_params("orthogonal_full_reuse"))
        self.assertAlmostEqual(bw_l + p.n_followers * bw_f, p.bandwidth_lu_hz)
        bw_l3, bw_f3 = _ground_branch_bandwidths(p, scenario_params("coordinated"))
        self.assertAlmostEqual(bw_l3 + p.n_followers * bw_f3, p.bandwidth_lu_hz / 3.0)

    def test_end_to_end_coverage_not_above_access_coverage(self) -> None:
        p = SystemParams(n_leaders=600, n_followers=5)
        samples = simulate_sinr_samples(p, scenario_params("coordinated", trials=1800, seed=41))
        thresholds = [-15.0, -10.0, -5.0]
        self.assertTrue(np.all(end_to_end_coverage_curve(samples, thresholds) <= access_coverage_curve(samples, thresholds) + 1e-12))

    def test_noise_limited_has_zero_interference(self) -> None:
        samples = simulate_sinr_samples(SystemParams(n_followers=5), scenario_params("noise_limited", trials=500, seed=42))
        self.assertEqual(float(np.max(samples["i_leader_rb"])), 0.0)
        self.assertEqual(float(np.max(samples["i_follower_rb"])), 0.0)

    def test_reuse_and_interference_gain_reduce_mean_interference(self) -> None:
        p = SystemParams(n_leaders=900, n_followers=10)
        theta = np.array([0.02, 0.05, 0.10])
        mu_base, _ = conditional_interference_moments(p, scenario_params("orthogonal_full_reuse"), theta, "leader")
        mu_coord, _ = conditional_interference_moments(p, scenario_params("coordinated"), theta, "leader")
        self.assertTrue(np.all(mu_coord < mu_base))

    def test_boundary_followers_are_nonzero_interferers(self) -> None:
        fraction = estimate_boundary_follower_interference_fraction(SystemParams(n_leaders=900), samples=100_000, seed=43)
        self.assertGreater(fraction, 0.0)

    def test_probabilities_are_valid(self) -> None:
        p = SystemParams(n_leaders=900, n_followers=10)
        samples = simulate_sinr_samples(p, scenario_params("orthogonal_full_reuse", trials=1200, seed=44))
        values = access_coverage_curve(samples, [-20.0, -10.0, 0.0])
        self.assertTrue(np.all((values >= 0.0) & (values <= 1.0)))
        self.assertTrue(np.all(np.diff(values) <= 1e-12))
        self.assertTrue(np.all(samples["sinr_lu"] >= 0.0))
        self.assertTrue(np.all(samples["cluster_rate_bps"] >= 0.0))

    def test_default_threshold_matches_stored_end_to_end_event(self) -> None:
        p = SystemParams(n_leaders=900, n_followers=5)
        samples = simulate_sinr_samples(p, scenario_params("coordinated", trials=1000, seed=45, gamma_lf_db=-2.0))
        computed = end_to_end_coverage_curve(samples, [p.gamma_th_db])[0]
        stored = np.mean(samples["coverage_e2e_default"])
        self.assertAlmostEqual(float(computed), float(stored))
        self.assertEqual(float(samples["gamma_lf_db"][0]), -2.0)
        self.assertGreaterEqual(db_to_linear(p.gamma_th_db), 0.0)

    def test_semi_analytical_accepts_threshold_generator(self) -> None:
        p = SystemParams(n_leaders=300, n_followers=0)
        coverage, rate = semi_analytical_leader_metrics(
            p,
            scenario_params("orthogonal_full_reuse"),
            (value for value in [-15.0, -10.0]),
            n_theta=24,
            n_interference=12,
        )
        self.assertEqual(coverage.shape, (2,))
        self.assertTrue(np.all(np.isfinite(coverage)))
        self.assertGreater(rate, 0.0)


if __name__ == "__main__":
    unittest.main()
