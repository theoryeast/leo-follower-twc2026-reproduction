from __future__ import annotations

import unittest

import numpy as np

from src.deployment_optimization_model import (
    DeploymentSearch,
    branch_sinr_for_alpha,
    cluster_rate_for_alpha,
    optimize_follower_count,
    run_deployment_validation,
)
from src.leo_follower_model import SystemParams
from src.sinr_model import scenario_params, simulate_sinr_samples


class DeploymentOptimizationTests(unittest.TestCase):
    def test_validation_gate(self) -> None:
        result = run_deployment_validation()
        self.assertTrue(result["all_acceptance_checks_pass"], result)

    def test_equal_alpha_reproduces_default_equal_rate(self) -> None:
        p = SystemParams(n_leaders=300, n_followers=5)
        sp = scenario_params("coordinated", trials=300, seed=61)
        samples = simulate_sinr_samples(p, sp)
        recomputed = cluster_rate_for_alpha(samples, p, sp, 1.0 / (p.n_followers + 1))
        self.assertTrue(np.allclose(recomputed, samples["cluster_rate_bps"]))

    def test_bandwidth_scaled_noise_makes_alpha_change_branch_sinr(self) -> None:
        p = SystemParams(n_leaders=300, n_followers=5)
        sp = scenario_params(
            "coordinated",
            trials=300,
            seed=64,
            bandwidth_scaled_noise=True,
        )
        samples = simulate_sinr_samples(p, sp)
        low_l, low_f = branch_sinr_for_alpha(samples, p, sp, 0.2)
        high_l, high_f = branch_sinr_for_alpha(samples, p, sp, 0.8)
        self.assertFalse(np.allclose(low_l, high_l))
        self.assertFalse(np.allclose(low_f, high_f))

    def test_optimization_returns_feasible_or_none(self) -> None:
        search = DeploymentSearch(
            follower_grid=(0, 5, 10),
            alpha_grid=(0.3, 0.5, 0.8),
            coverage_target=0.5,
            conservative_constraint=False,
        )
        best, candidates = optimize_follower_count(
            300,
            scenario_params("coordinated", trials=250, seed=62),
            search,
        )
        self.assertGreater(len(candidates), 0)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertGreaterEqual(best["e2e_coverage"], search.coverage_target)
        self.assertTrue(best["selected"])

    def test_conservative_selection_is_independently_validated(self) -> None:
        search = DeploymentSearch(
            follower_grid=(0, 5),
            alpha_grid=(0.5, 0.8),
            coverage_target=0.2,
            conservative_constraint=True,
            independent_validation=True,
            validation_trials=500,
        )
        best, candidates = optimize_follower_count(
            300,
            scenario_params("coordinated", trials=500, seed=63),
            search,
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertTrue(best["selected"])
        self.assertTrue(best["validation_feasible"])
        self.assertGreaterEqual(best["e2e_coverage_ci_low"], search.coverage_target)
        self.assertGreaterEqual(best["validation_e2e_coverage_ci_low"], search.coverage_target)
        self.assertEqual(sum(bool(row["selected"]) for row in candidates), 1)

    def test_rate_tolerance_selects_smallest_near_optimal_follower_count(self) -> None:
        search = DeploymentSearch(
            follower_grid=(0, 2, 5),
            alpha_grid=(0.5, 0.8),
            coverage_target=0.1,
            conservative_constraint=True,
            rate_tolerance_relative=1.0,
        )
        best, candidates = optimize_follower_count(
            300,
            scenario_params("coordinated", trials=300, seed=65),
            search,
        )
        self.assertIsNotNone(best)
        assert best is not None
        feasible_nfs = [int(row["n_followers"]) for row in candidates if row["feasible"]]
        self.assertEqual(int(best["n_followers"]), min(feasible_nfs))

    def test_validation_reselection_and_exact_correlated_audit(self) -> None:
        search = DeploymentSearch(
            follower_grid=(0, 2, 5),
            alpha_grid=(0.35, 0.5, 0.8),
            coverage_target=0.1,
            conservative_constraint=True,
            independent_validation=True,
            validation_trials=450,
            rate_tolerance_relative=0.1,
            reselect_on_validation=True,
            exact_audit=True,
            exact_audit_trials=350,
            exact_audit_shared_reuse_color=True,
        )
        best, candidates = optimize_follower_count(
            180,
            scenario_params(
                "coordinated",
                trials=350,
                seed=66,
                bandwidth_scaled_noise=True,
            ),
            search,
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertTrue(best["selected"])
        self.assertTrue(best["validation_feasible"])
        self.assertTrue(best["validation_within_rate_tolerance"])
        self.assertTrue(best["exact_audit_feasible"])
        self.assertTrue(best["exact_audit_shared_reuse_color"])
        self.assertEqual(sum(bool(row["selected"]) for row in candidates), 1)
        self.assertTrue(all("validation_mean_rate_gbps" in row for row in candidates))


if __name__ == "__main__":
    unittest.main()
