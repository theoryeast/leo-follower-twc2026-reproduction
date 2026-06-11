"""Deployment optimization utilities for the resource-consistent SINR study."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.leo_follower_model import SystemParams, db_to_linear
from src.sinr_model import (
    SinrParams,
    binomial_confidence_interval,
    effective_system_params,
    scenario_params,
    simulate_sinr_samples,
)


@dataclass(frozen=True)
class DeploymentSearch:
    follower_grid: tuple[int, ...] = (0, 2, 5, 10, 15, 20, 30)
    alpha_grid: tuple[float, ...] = (0.2, 0.35, 0.5, 0.65, 0.8)
    coverage_target: float = 0.80
    conservative_constraint: bool = True
    independent_validation: bool = False
    validation_trials: int = 4000
    validation_seed_offset: int = 700_001
    rate_tolerance_relative: float = 0.0
    reselect_on_validation: bool = False
    exact_audit: bool = False
    exact_audit_trials: int = 2500
    exact_audit_seed_offset: int = 1_400_003
    exact_audit_shared_reuse_color: bool = True


def branch_sinr_for_alpha(
    samples: dict[str, np.ndarray],
    p: SystemParams,
    sp: SinrParams,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Recompute branch SINRs when thermal noise scales with allocated bandwidth."""
    if not sp.bandwidth_scaled_noise:
        return samples["sinr_lu"], samples["sinr_fu"]
    nf = p.n_followers
    reuse = max(sp.reuse_factor, 1)
    if nf == 0:
        noise_l = 1.0 / reuse
        return samples["desired_lu_normalized"] / (noise_l + samples["i_leader_rb"]), samples["sinr_fu"]
    alpha = min(max(float(alpha), 0.0), 1.0)
    noise_l = max(alpha / reuse, 1e-15)
    noise_f = max((1.0 - alpha) / (nf * reuse), 1e-15)
    sinr_l = samples["desired_lu_normalized"] / (noise_l + samples["i_leader_rb"])
    sinr_f = samples["desired_fu_normalized"] / (noise_f + samples["i_follower_rb"])
    return sinr_l, sinr_f


def cluster_rate_for_alpha(
    samples: dict[str, np.ndarray],
    p: SystemParams,
    sp: SinrParams,
    alpha: float,
) -> np.ndarray:
    """Recompute the symmetric-allocation cluster rate from fixed SINR samples."""
    nf = p.n_followers
    reuse = max(sp.reuse_factor, 1)
    if nf == 0:
        bw_l = p.bandwidth_lu_hz / reuse
        sinr_l, _ = branch_sinr_for_alpha(samples, p, sp, 1.0)
        return bw_l * np.log2(1.0 + sinr_l)
    alpha = min(max(float(alpha), 0.0), 1.0)
    bw_l = alpha * p.bandwidth_lu_hz / reuse
    bw_f = (1.0 - alpha) * p.bandwidth_fu_hz / (nf * reuse)
    sinr_l, sinr_f = branch_sinr_for_alpha(samples, p, sp, alpha)
    rate_l = bw_l * np.log2(1.0 + sinr_l)
    rate_f = bw_f * np.log2(1.0 + sinr_f)
    relay = sp.isl_duplex_factor * np.minimum(samples["rate_lf_bps"], rate_f)
    return rate_l + np.sum(relay, axis=1)


def _rate_summary(rate_bps: np.ndarray) -> dict[str, float]:
    rate_bps = np.asarray(rate_bps, dtype=float)
    mean = float(np.mean(rate_bps))
    std = float(np.std(rate_bps, ddof=1)) if rate_bps.size > 1 else 0.0
    half = 1.959963984540054 * std / math.sqrt(max(rate_bps.size, 1))
    return {
        "mean_rate_gbps": mean / 1e9,
        "rate_ci_low_gbps": (mean - half) / 1e9,
        "rate_ci_high_gbps": (mean + half) / 1e9,
        "rate_p05_gbps": float(np.quantile(rate_bps, 0.05)) / 1e9,
        "rate_median_gbps": float(np.quantile(rate_bps, 0.50)) / 1e9,
        "rate_p95_gbps": float(np.quantile(rate_bps, 0.95)) / 1e9,
    }


def evaluate_samples(
    samples: dict[str, np.ndarray],
    p: SystemParams,
    sp: SinrParams,
    alpha: float,
) -> dict[str, float]:
    rate = cluster_rate_for_alpha(samples, p, sp, alpha)
    sinr_l, sinr_f = branch_sinr_for_alpha(samples, p, sp, alpha)
    if p.n_followers:
        success_vector = (sinr_l >= p.gamma_th_linear) | np.any(
            (sinr_f >= p.gamma_th_linear)
            & (samples["snr_lf"] >= db_to_linear(sp.gamma_lf_db)),
            axis=1,
        )
        access_best = np.maximum(sinr_l, np.max(sinr_f, axis=1))
    else:
        success_vector = sinr_l >= p.gamma_th_linear
        access_best = sinr_l
    success = int(np.sum(success_vector))
    trials = int(success_vector.size)
    coverage, coverage_low, coverage_high = binomial_confidence_interval(success, trials)
    access = float(np.mean(access_best >= db_to_linear(p.gamma_th_db)))
    out = _rate_summary(rate)
    out.update(
        {
            "alpha": float(alpha),
            "e2e_coverage": coverage,
            "e2e_coverage_ci_low": coverage_low,
            "e2e_coverage_ci_high": coverage_high,
            "access_coverage": access,
            "trials": trials,
        }
    )
    return out


def optimize_symmetric_bandwidth(
    samples: dict[str, np.ndarray],
    p: SystemParams,
    sp: SinrParams,
    alphas: Iterable[float],
    coverage_target: float,
    conservative_constraint: bool = True,
) -> tuple[dict[str, float] | None, list[dict[str, float]]]:
    """Solve the continuous inner problem over a finite symmetric alpha grid."""
    if p.n_followers == 0:
        alphas = [1.0]
    rows = [evaluate_samples(samples, p, sp, alpha) for alpha in alphas]
    coverage_key = "e2e_coverage_ci_low" if conservative_constraint else "e2e_coverage"
    feasible = [row for row in rows if row[coverage_key] >= coverage_target]
    if not feasible:
        return None, rows
    return max(feasible, key=lambda row: row["mean_rate_gbps"]), rows


def optimize_follower_count(
    n_leaders: int,
    sp_template: SinrParams,
    search: DeploymentSearch,
    system_updates: dict[str, float] | None = None,
) -> tuple[dict[str, float] | None, list[dict[str, float]]]:
    """Outer enumeration over follower count with optional independent validation."""
    system_updates = {} if system_updates is None else dict(system_updates)
    candidates: list[dict[str, float]] = []
    for idx, nf in enumerate(search.follower_grid):
        p = SystemParams(n_leaders=int(n_leaders), n_followers=int(nf)).with_updates(**system_updates)
        sp = sp_template.with_updates(seed=sp_template.seed + 1009 * idx)
        samples = simulate_sinr_samples(p, sp)
        best, rows = optimize_symmetric_bandwidth(
            samples,
            p,
            sp,
            search.alpha_grid,
            search.coverage_target,
            search.conservative_constraint,
        )
        for row in rows:
            row.update(
                {
                    "n_leaders": int(n_leaders),
                    "n_followers": int(nf),
                    "reuse_factor": int(sp.reuse_factor),
                    "activity_probability": float(sp.activity_probability),
                    "interference_gain_db": float(sp.interference_gain_db),
                    "power_model": sp.power_model,
                    "leader_power_fraction": float(sp.leader_power_fraction),
                    "follower_availability_probability": float(sp.follower_availability_probability),
                    "gamma_th_db": float(p.gamma_th_db),
                    "gamma_lf_db": float(sp.gamma_lf_db),
                    "scan_interference_method": sp.interference_method,
                    "scan_shared_reuse_color": bool(sp.shared_reuse_color),
                    "feasible": bool(
                        row["e2e_coverage_ci_low" if search.conservative_constraint else "e2e_coverage"]
                        >= search.coverage_target
                    ),
                    "selected": False,
                    "selection_constraint": (
                        "e2e_coverage_ci_low"
                        if search.conservative_constraint
                        else "e2e_coverage"
                    ),
                }
            )
            candidates.append(row)
        if best is not None:
            best["n_followers"] = int(nf)
    feasible_best = [row for row in candidates if row["feasible"]]
    if not feasible_best and not (
        search.independent_validation and search.reselect_on_validation
    ):
        return None, candidates
    best_by_nf: dict[int, dict[str, float]] = {}
    for row in feasible_best:
        nf = int(row["n_followers"])
        if nf not in best_by_nf or row["mean_rate_gbps"] > best_by_nf[nf]["mean_rate_gbps"]:
            best_by_nf[nf] = row
    per_nf = list(best_by_nf.values())
    maximum_rate = (
        max(row["mean_rate_gbps"] for row in per_nf)
        if per_nf
        else float("nan")
    )
    tolerance = min(max(search.rate_tolerance_relative, 0.0), 1.0)
    near_optimal = [
        row
        for row in per_nf
        if row["mean_rate_gbps"] >= (1.0 - tolerance) * maximum_rate
    ]
    if tolerance > 0.0:
        ranked = sorted(
            near_optimal,
            key=lambda row: (int(row["n_followers"]), -row["mean_rate_gbps"]),
        )
    else:
        ranked = sorted(per_nf, key=lambda row: row["mean_rate_gbps"], reverse=True)
    for row in candidates:
        row["maximum_feasible_rate_gbps"] = maximum_rate
        row["within_rate_tolerance"] = bool(
            row["feasible"]
            and row["mean_rate_gbps"] >= (1.0 - tolerance) * maximum_rate
        )
        row["rate_tolerance_relative"] = tolerance
    if not search.independent_validation:
        selected = ranked[0]
        selected["selected"] = True
        return selected, candidates

    validation_rows: list[dict[str, float]] = []
    if search.reselect_on_validation:
        validation_groups = [
            [
                row
                for row in candidates
                if int(row["n_followers"]) == int(nf)
            ]
            for nf in search.follower_grid
        ]
        validation_groups = [group for group in validation_groups if group]
    else:
        validation_groups = [[candidate] for candidate in ranked]

    for rank, group in enumerate(validation_groups, start=1):
        representative = group[0]
        p = SystemParams(
            n_leaders=int(n_leaders),
            n_followers=int(representative["n_followers"]),
        ).with_updates(**system_updates)
        validation_sp = sp_template.with_updates(
            trials=search.validation_trials,
            seed=sp_template.seed
            + search.validation_seed_offset
            + 1009 * int(representative["n_followers"])
            + rank,
        )
        validation_samples = simulate_sinr_samples(p, validation_sp)
        for candidate in group:
            validation = evaluate_samples(
                validation_samples,
                p,
                validation_sp,
                float(candidate["alpha"]),
            )
            validation_feasible = bool(
                validation[
                    "e2e_coverage_ci_low"
                    if search.conservative_constraint
                    else "e2e_coverage"
                ]
                >= search.coverage_target
            )
            candidate.update(
                {
                    "validation_rank": rank,
                    "validation_trials": search.validation_trials,
                    "validation_mean_rate_gbps": validation["mean_rate_gbps"],
                    "validation_rate_ci_low_gbps": validation["rate_ci_low_gbps"],
                    "validation_rate_ci_high_gbps": validation["rate_ci_high_gbps"],
                    "validation_e2e_coverage": validation["e2e_coverage"],
                    "validation_e2e_coverage_ci_low": validation["e2e_coverage_ci_low"],
                    "validation_e2e_coverage_ci_high": validation["e2e_coverage_ci_high"],
                    "validation_feasible": validation_feasible,
                    "validation_interference_method": validation_sp.interference_method,
                    "validation_shared_reuse_color": bool(validation_sp.shared_reuse_color),
                }
            )
            validation_rows.append(candidate)

    if search.reselect_on_validation:
        validation_feasible_rows = [
            row for row in validation_rows if bool(row["validation_feasible"])
        ]
        if not validation_feasible_rows:
            return None, candidates
        validation_maximum_rate = max(
            float(row["validation_mean_rate_gbps"])
            for row in validation_feasible_rows
        )
        validation_near_optimal = [
            row
            for row in validation_feasible_rows
            if float(row["validation_mean_rate_gbps"])
            >= (1.0 - tolerance) * validation_maximum_rate
        ]
        if tolerance > 0.0:
            ranked = sorted(
                validation_near_optimal,
                key=lambda row: (
                    int(row["n_followers"]),
                    -float(row["validation_mean_rate_gbps"]),
                ),
            )
        else:
            ranked = sorted(
                validation_feasible_rows,
                key=lambda row: float(row["validation_mean_rate_gbps"]),
                reverse=True,
            )
        for row in candidates:
            row["validation_maximum_feasible_rate_gbps"] = validation_maximum_rate
            row["validation_within_rate_tolerance"] = bool(
                row.get("validation_feasible", False)
                and float(row.get("validation_mean_rate_gbps", -math.inf))
                >= (1.0 - tolerance) * validation_maximum_rate
            )
    else:
        ranked = [
            row for row in validation_rows if bool(row["validation_feasible"])
        ]

    if not ranked:
        return None, candidates

    if not search.exact_audit:
        ranked[0]["selected"] = True
        return ranked[0], candidates

    for audit_rank, candidate in enumerate(ranked, start=1):
        p = SystemParams(
            n_leaders=int(n_leaders),
            n_followers=int(candidate["n_followers"]),
        ).with_updates(**system_updates)
        audit_sp = sp_template.with_updates(
            trials=search.exact_audit_trials,
            seed=sp_template.seed
            + search.exact_audit_seed_offset
            + 1009 * int(candidate["n_followers"])
            + audit_rank,
            interference_method="exact",
            shared_reuse_color=search.exact_audit_shared_reuse_color,
        )
        audit_samples = simulate_sinr_samples(p, audit_sp)
        audit = evaluate_samples(
            audit_samples,
            p,
            audit_sp,
            float(candidate["alpha"]),
        )
        audit_feasible = bool(
            audit[
                "e2e_coverage_ci_low"
                if search.conservative_constraint
                else "e2e_coverage"
            ]
            >= search.coverage_target
        )
        candidate.update(
            {
                "exact_audit_rank": audit_rank,
                "exact_audit_trials": search.exact_audit_trials,
                "exact_audit_shared_reuse_color": search.exact_audit_shared_reuse_color,
                "exact_audit_mean_rate_gbps": audit["mean_rate_gbps"],
                "exact_audit_rate_ci_low_gbps": audit["rate_ci_low_gbps"],
                "exact_audit_rate_ci_high_gbps": audit["rate_ci_high_gbps"],
                "exact_audit_e2e_coverage": audit["e2e_coverage"],
                "exact_audit_e2e_coverage_ci_low": audit["e2e_coverage_ci_low"],
                "exact_audit_e2e_coverage_ci_high": audit["e2e_coverage_ci_high"],
                "exact_audit_feasible": audit_feasible,
            }
        )
        if audit_feasible:
            candidate["selected"] = True
            return candidate, candidates
    return None, candidates


def correlation_diagnostics(
    p: SystemParams,
    sp_template: SinrParams,
) -> dict[str, float]:
    """Compare exact-RB interference correlation with and without common reuse color."""
    independent = simulate_sinr_samples(
        p,
        sp_template.with_updates(interference_method="exact", shared_reuse_color=False),
    )
    shared = simulate_sinr_samples(
        p,
        sp_template.with_updates(interference_method="exact", shared_reuse_color=True),
    )
    if p.n_followers == 0:
        return {
            "independent_rb_correlation": float("nan"),
            "shared_color_correlation": float("nan"),
        }
    return {
        "independent_rb_correlation": float(
            np.corrcoef(independent["i_leader_rb"], independent["i_follower_rb"][:, 0])[0, 1]
        ),
        "shared_color_correlation": float(
            np.corrcoef(shared["i_leader_rb"], shared["i_follower_rb"][:, 0])[0, 1]
        ),
        "independent_mean_leader_inr": float(np.mean(independent["i_leader_rb"])),
        "shared_mean_leader_inr": float(np.mean(shared["i_leader_rb"])),
        "independent_e2e_coverage": float(np.mean(independent["coverage_e2e_default"])),
        "shared_e2e_coverage": float(np.mean(shared["coverage_e2e_default"])),
    }


def run_deployment_validation() -> dict[str, float | bool]:
    p = SystemParams(n_leaders=300, n_followers=5)
    coordinated = scenario_params("coordinated", trials=700, seed=9300)
    samples = simulate_sinr_samples(p, coordinated)
    equal_alpha = 1.0 / (p.n_followers + 1)
    recomputed = cluster_rate_for_alpha(samples, p, coordinated, equal_alpha)

    fixed = coordinated.with_updates(
        power_model="fixed_cluster_total",
        cluster_power_dbw=20.0,
        leader_power_fraction=0.4,
    )
    p_eff = effective_system_params(p, fixed)
    total_power = 10.0 ** (p_eff.rho_lu_dbw / 10.0) + p.n_followers * 10.0 ** (p_eff.rho_fu_dbw / 10.0)

    unavailable = simulate_sinr_samples(
        p,
        coordinated.with_updates(follower_availability_probability=0.0, seed=9301),
    )
    correlation = correlation_diagnostics(
        SystemParams(n_leaders=300, n_followers=3),
        coordinated.with_updates(trials=900, seed=9302, interference_gain_db=-10.0),
    )
    checks: dict[str, float | bool] = {
        "equal_rate_recompute_max_relative_error": float(
            np.max(np.abs(recomputed - samples["cluster_rate_bps"]))
            / max(float(np.max(samples["cluster_rate_bps"])), 1e-12)
        ),
        "fixed_cluster_power_relative_error": abs(total_power - 10.0 ** (fixed.cluster_power_dbw / 10.0))
        / 10.0 ** (fixed.cluster_power_dbw / 10.0),
        "zero_availability_zero_relay": bool(float(np.max(unavailable["rate_relay_bps"])) == 0.0),
        **correlation,
    }
    coverage_invariance = [
        evaluate_samples(samples, p, coordinated, alpha)["e2e_coverage"]
        for alpha in (0.2, 0.5, 0.8)
    ]
    scaled_noise = coordinated.with_updates(bandwidth_scaled_noise=True, seed=9303)
    scaled_samples = simulate_sinr_samples(p, scaled_noise)
    scaled_low_l, scaled_low_f = branch_sinr_for_alpha(scaled_samples, p, scaled_noise, 0.2)
    scaled_high_l, scaled_high_f = branch_sinr_for_alpha(scaled_samples, p, scaled_noise, 0.8)
    checks["sinr_coverage_alpha_invariance_max_error"] = float(
        np.max(np.abs(np.asarray(coverage_invariance) - coverage_invariance[0]))
    )
    checks["bandwidth_scaled_noise_changes_branch_sinr"] = bool(
        not np.allclose(scaled_low_l, scaled_high_l)
        and not np.allclose(scaled_low_f, scaled_high_f)
    )
    checks["shared_color_increases_correlation"] = bool(
        correlation["shared_color_correlation"] > correlation["independent_rb_correlation"]
    )
    checks["all_acceptance_checks_pass"] = bool(
        checks["equal_rate_recompute_max_relative_error"] < 1e-12
        and checks["fixed_cluster_power_relative_error"] < 1e-12
        and checks["zero_availability_zero_relay"]
        and checks["shared_color_increases_correlation"]
        and checks["sinr_coverage_alpha_invariance_max_error"] < 1e-15
        and checks["bandwidth_scaled_noise_changes_branch_sinr"]
    )
    return checks


if __name__ == "__main__":
    import json

    print(json.dumps(run_deployment_validation(), indent=2, ensure_ascii=False))
