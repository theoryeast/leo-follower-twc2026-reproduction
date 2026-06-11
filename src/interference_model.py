"""Inter-cluster interference extension for follower-based LEO clusters.

The baseline reproduction is noise-limited.  This module adds a same-frequency
downlink model in which every non-serving leader cluster contributes aggregate
leader and follower interference at the typical ground user.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.leo_follower_model import (
    SystemParams,
    average_rate_cluster_middle,
    average_rate_cluster_monte_carlo,
    db_to_linear,
    expected_log2_gamma,
    f_theta_lu,
    f_theta_fu_max,
    f_theta_fu_min,
    r_fu,
    r_lf,
    r_su,
    sample_fading,
    sample_psi_cap,
    sample_theta_lu,
    sr_gamma_parameters,
    xi_fu,
    xi_lf,
    xi_lu,
)


@dataclass(frozen=True)
class InterferenceParams:
    trials: int = 1600
    seed: int = 20260601
    leader_chunk: int = 256
    follower_samples_per_cluster: int = 2
    theta_visible_rad: float | None = None
    include_leader_interference: bool = True
    include_follower_interference: bool = True
    interference_enabled: bool = True

    def with_updates(self, **kwargs) -> "InterferenceParams":
        return replace(self, **kwargs)


def _theta_visible(p: SystemParams, ip: InterferenceParams) -> float:
    return p.theta_max_rad if ip.theta_visible_rad is None else ip.theta_visible_rad


def confidence_interval(values: np.ndarray, confidence: float = 0.95) -> tuple[float, float, float]:
    vals = np.asarray(values, dtype=float)
    mean = float(np.mean(vals))
    if vals.size <= 1:
        return mean, mean, mean
    z = 1.959963984540054 if confidence == 0.95 else 1.0
    half = z * float(np.std(vals, ddof=1)) / math.sqrt(vals.size)
    return mean, mean - half, mean + half


def _sample_other_leader_cos(
    cos_theta0: np.ndarray,
    count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample other leaders uniformly on the sphere outside the serving cap."""
    u = rng.random((cos_theta0.size, count))
    return -1.0 + u * (cos_theta0[:, None] + 1.0)


def _cos_follower_contact(theta: np.ndarray, psi: np.ndarray, phi: np.ndarray) -> np.ndarray:
    return np.sin(theta) * np.sin(psi) * np.cos(phi) + np.cos(theta) * np.cos(psi)


def _aggregate_interference(
    p: SystemParams,
    ip: InterferenceParams,
    theta0: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not ip.interference_enabled:
        z = np.zeros(theta0.size)
        return z, z, z

    visible = _theta_visible(p, ip)
    cos_visible = math.cos(visible)
    cos_theta0 = np.cos(theta0)
    n_other = max(p.n_leaders - 1, 0)
    i_l = np.zeros(theta0.size)
    i_f = np.zeros(theta0.size)
    if n_other == 0:
        return i_l, i_f, i_l + i_f

    k_follow = max(1, ip.follower_samples_per_cluster)
    for start in range(0, n_other, ip.leader_chunk):
        count = min(ip.leader_chunk, n_other - start)
        cos_t = _sample_other_leader_cos(cos_theta0, count, rng)
        mask = cos_t >= cos_visible
        theta = np.arccos(np.clip(cos_t, -1.0, 1.0))
        if ip.include_leader_interference:
            w_l = sample_fading(theta.shape, p, rng)
            i_l += np.sum(mask * xi_lu(p) * w_l / (r_su(theta, p) ** 2), axis=1)
        if ip.include_follower_interference and p.n_followers > 0:
            acc = np.zeros(theta.shape)
            for _ in range(k_follow):
                psi = sample_psi_cap(theta.shape, p, rng)
                phi = rng.uniform(0.0, 2.0 * math.pi, size=theta.shape)
                w_f = sample_fading(theta.shape, p, rng)
                follower_visible = _cos_follower_contact(theta, psi, phi) >= cos_visible
                acc += follower_visible * xi_fu(p) * w_f / (r_fu(theta, psi, phi, p) ** 2)
            # A follower can be visible even when its parent leader is just
            # outside the visibility boundary.  Do not apply the leader mask.
            i_f += np.sum((p.n_followers / k_follow) * acc, axis=1)
    return i_l, i_f, i_l + i_f


def simulate_network_samples(
    p: SystemParams,
    ip: InterferenceParams | None = None,
) -> dict[str, np.ndarray]:
    ip = InterferenceParams() if ip is None else ip
    rng = np.random.default_rng(ip.seed + 101 * p.n_leaders + 17 * p.n_followers)
    theta0 = sample_theta_lu(ip.trials, p, rng)
    i_l, i_f, i_total = _aggregate_interference(p, ip, theta0, rng)

    w_lu = sample_fading(ip.trials, p, rng)
    s_lu = xi_lu(p) * w_lu / (r_su(theta0, p) ** 2)
    sinr_lu = s_lu / (1.0 + i_total)
    rate_lu = p.bandwidth_lu_hz * np.log2(1.0 + sinr_lu)

    if p.n_followers > 0:
        psi = sample_psi_cap((ip.trials, p.n_followers), p, rng)
        phi = rng.uniform(0.0, 2.0 * math.pi, size=(ip.trials, p.n_followers))
        w_fu = sample_fading((ip.trials, p.n_followers), p, rng)
        dist_fu = r_fu(theta0[:, None], psi, phi, p)
        sinr_fu = xi_fu(p) * w_fu / (dist_fu**2) / (1.0 + i_total[:, None])
        rate_fu = p.bandwidth_fu_hz * np.log2(1.0 + sinr_fu)
        rate_lf = p.bandwidth_lf_hz * np.log2(1.0 + xi_lf(p) / (r_lf(psi, p) ** 2))
        cluster_rate = rate_lu + np.sum(np.minimum(rate_lf, rate_fu), axis=1)
        best_branch_sinr = np.maximum(sinr_lu, np.max(sinr_fu, axis=1))
    else:
        cluster_rate = rate_lu
        best_branch_sinr = sinr_lu

    return {
        "theta0": theta0,
        "i_leader": i_l,
        "i_follower": i_f,
        "i_total": i_total,
        "sinr_lu": sinr_lu,
        "sinr_best": best_branch_sinr,
        "rate_lu_bps": rate_lu,
        "cluster_rate_bps": cluster_rate,
    }


def summarize_samples(samples: dict[str, np.ndarray]) -> dict[str, float]:
    rate_mean, rate_lo, rate_hi = confidence_interval(samples["cluster_rate_bps"])
    inr_mean, inr_lo, inr_hi = confidence_interval(samples["i_total"])
    return {
        "mean_inr": inr_mean,
        "mean_inr_ci_low": inr_lo,
        "mean_inr_ci_high": inr_hi,
        "mean_leader_inr": float(np.mean(samples["i_leader"])),
        "mean_follower_inr": float(np.mean(samples["i_follower"])),
        "mean_rate_bps": rate_mean,
        "mean_rate_ci_low": rate_lo,
        "mean_rate_ci_high": rate_hi,
        "mean_rate_gbps": rate_mean / 1e9,
        "mean_rate_ci_low_gbps": rate_lo / 1e9,
        "mean_rate_ci_high_gbps": rate_hi / 1e9,
    }


def coverage_curve(samples: dict[str, np.ndarray], thresholds_db: Iterable[float]) -> np.ndarray:
    sinr = samples["sinr_best"]
    return np.array([np.mean(sinr >= db_to_linear(th)) for th in thresholds_db], dtype=float)


def mean_field_leader_coverage(
    p: SystemParams,
    thresholds_db: Iterable[float],
    inr: float | None = None,
    n_theta: int = 160,
) -> np.ndarray:
    """Semi-analytical LU SINR coverage under a deterministic mean INR penalty."""
    from scipy.special import gammaincc

    inr = mean_interference_inr(p) if inr is None else float(inr)
    shape, scale = sr_gamma_parameters(p)
    x, w = np.polynomial.legendre.leggauss(n_theta)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    density = f_theta_lu(theta, p)
    out = []
    for th_db in thresholds_db:
        gamma_th = db_to_linear(th_db)
        fading_arg = gamma_th * (1.0 + inr) * (r_su(theta, p) ** 2) / xi_lu(p)
        survival = gammaincc(shape, fading_arg / scale)
        out.append(float(np.sum(wtheta * density * survival)))
    return np.array(out, dtype=float)


def _mean_fading(p: SystemParams) -> float:
    shape, scale = sr_gamma_parameters(p)
    return shape * scale


def mean_interference_coefficients(
    p: SystemParams,
    n_theta0: int = 60,
    n_theta: int = 36,
    n_psi: int = 10,
    n_phi: int = 12,
) -> tuple[float, float]:
    """Return mean INR contributions per network as leader_coeff + NF*follow_coeff.

    The expectation is over the serving contact angle and the conditional
    distribution of all non-serving clusters.  Values are normalized by noise.
    """
    if p.n_leaders <= 1:
        return 0.0, 0.0
    visible = p.theta_max_rad
    fmax = 1.0 - ((1.0 + math.cos(visible)) / 2.0) ** p.n_leaders
    x0, w0 = np.polynomial.legendre.leggauss(n_theta0)
    theta0s = 0.5 * visible * (x0 + 1.0)
    wtheta0 = 0.5 * visible * w0
    xp, wp = np.polynomial.legendre.leggauss(n_psi)
    xf, wf = np.polynomial.legendre.leggauss(n_phi)
    psi = 0.5 * p.theta_cap_rad * (xp + 1.0)
    wpsi = 0.5 * p.theta_cap_rad * wp
    phi = math.pi * (xf + 1.0)
    wphi = math.pi * wf
    psi_grid = psi[:, None]
    phi_grid = phi[None, :]
    cap_weights = wpsi[:, None] * wphi[None, :] * np.sin(psi_grid)
    cap_weights /= 2.0 * math.pi * (1.0 - math.cos(p.theta_cap_rad))
    ew = _mean_fading(p)
    leader_acc = 0.0
    follower_acc = 0.0
    for theta0, wt0 in zip(theta0s, wtheta0):
        density0 = f_theta_lu(theta0, p) / max(fmax, 1e-15)
        if theta0 >= visible:
            continue
        xt, wt = np.polynomial.legendre.leggauss(n_theta)
        theta = 0.5 * (visible - theta0) * (xt + 1.0) + theta0
        wtheta = 0.5 * (visible - theta0) * wt
        cond_pdf = np.sin(theta) / (1.0 + math.cos(theta0))
        leader_one = np.sum(wtheta * cond_pdf * xi_lu(p) * ew / (r_su(theta, p) ** 2))
        follower_one = 0.0
        follower_end = min(math.pi, visible + p.theta_cap_rad)
        theta_f = 0.5 * (follower_end - theta0) * (xt + 1.0) + theta0
        wtheta_f = 0.5 * (follower_end - theta0) * wt
        cond_pdf_f = np.sin(theta_f) / (1.0 + math.cos(theta0))
        for th, ww in zip(theta_f, wtheta_f * cond_pdf_f):
            cos_contact = _cos_follower_contact(th, psi_grid, phi_grid)
            visible_mask = cos_contact >= math.cos(visible)
            dist = r_fu(th, psi_grid, phi_grid, p)
            follower_one += ww * float(np.sum(visible_mask * cap_weights * xi_fu(p) * ew / (dist**2)))
        leader_acc += wt0 * density0 * leader_one
        follower_acc += wt0 * density0 * follower_one
    scale = p.n_leaders - 1
    return scale * leader_acc, scale * follower_acc


def mean_interference_inr(p: SystemParams) -> float:
    leader, follower = mean_interference_coefficients(p)
    return leader + p.n_followers * follower


def average_rate_cluster_middle_with_interference(p: SystemParams, inr: float) -> float:
    """Corollary-2-style middle rate with a deterministic mean INR penalty."""
    effective = 1.0 + max(float(inr), 0.0)
    x, w = np.polynomial.legendre.leggauss(160)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    leader_spectral = expected_log2_gamma((xi_lu(p) / effective) / (r_su(theta, p) ** 2), p)
    leader_rate = float(p.bandwidth_lu_hz * np.sum(wtheta * leader_spectral * f_theta_lu(theta, p)))
    if p.n_followers <= 0:
        return leader_rate

    def follower_bound(bound: str) -> float:
        if bound == "upper":
            mass_zero = 1.0 - ((1.0 + math.cos(p.theta_cap_rad)) / 2.0) ** p.n_leaders
            a0 = (xi_fu(p) / effective) / (r_su(0.0, p) ** 2)
            zero_rate = mass_zero * expected_log2_gamma(a0, p)
            end = max(p.theta_max_rad - p.theta_cap_rad, 1e-9)
            xb, wb = np.polynomial.legendre.leggauss(160)
            th = 0.5 * end * (xb + 1.0)
            ww = 0.5 * end * wb
            density = f_theta_fu_min(th, p)
            spectral = expected_log2_gamma((xi_fu(p) / effective) / (r_su(th, p) ** 2), p)
            return float(p.bandwidth_fu_hz * (zero_rate + np.sum(ww * spectral * density)))
        start = p.theta_cap_rad
        end = p.theta_max_rad + p.theta_cap_rad
        xb, wb = np.polynomial.legendre.leggauss(160)
        th = 0.5 * (end - start) * (xb + 1.0) + start
        ww = 0.5 * (end - start) * wb
        density = f_theta_fu_max(th, p)
        spectral = expected_log2_gamma((xi_fu(p) / effective) / (r_su(th, p) ** 2), p)
        return float(p.bandwidth_fu_hz * np.sum(ww * spectral * density))

    return leader_rate + p.n_followers * 0.5 * (follower_bound("upper") + follower_bound("lower"))


def run_interference_sanity_checks() -> dict[str, float | bool]:
    base = SystemParams(n_leaders=900, n_followers=10)
    no_i_samples = simulate_network_samples(base, InterferenceParams(trials=1200, interference_enabled=False, seed=12))
    no_i_rate = float(np.mean(no_i_samples["cluster_rate_bps"]))
    baseline_rate = average_rate_cluster_middle(base)
    baseline_mc_rate = average_rate_cluster_monte_carlo(base, samples=1200, seed=12)
    nf0_samples = simulate_network_samples(base.with_updates(n_followers=0), InterferenceParams(trials=500, seed=13))
    nf10_samples = simulate_network_samples(base.with_updates(n_followers=10), InterferenceParams(trials=500, seed=13))
    nl1200_samples = simulate_network_samples(base.with_updates(n_leaders=1200, n_followers=10), InterferenceParams(trials=500, seed=13))
    nf0 = summarize_samples(nf0_samples)
    nf10 = summarize_samples(nf10_samples)
    nl1200 = summarize_samples(nl1200_samples)
    finite = all(np.isfinite(v) for v in [no_i_rate, baseline_rate, baseline_mc_rate, nf0["mean_inr"], nf10["mean_inr"], nl1200["mean_inr"]])
    no_i_rel_to_mc = abs(no_i_rate - baseline_mc_rate) / max(baseline_mc_rate, 1.0)
    return {
        "finite_outputs": bool(finite),
        "no_interference_rate_gbps": no_i_rate / 1e9,
        "baseline_middle_rate_gbps": baseline_rate / 1e9,
        "baseline_mc_rate_gbps": baseline_mc_rate / 1e9,
        "no_interference_relative_error": abs(no_i_rate - baseline_rate) / max(baseline_rate, 1.0),
        "no_interference_relative_error_vs_mc": no_i_rel_to_mc,
        "no_interference_recovers_mc": bool(no_i_rel_to_mc < 0.08),
        "nf0_mean_inr": nf0["mean_inr"],
        "nf10_mean_inr": nf10["mean_inr"],
        "nl1200_nf10_mean_inr": nl1200["mean_inr"],
        "nf_increases_interference": bool(nf10["mean_inr"] >= nf0["mean_inr"]),
        "nl_increases_interference": bool(nl1200["mean_inr"] >= nf10["mean_inr"]),
        "nf0_rate_positive": bool(nf0["mean_rate_bps"] > 0.0),
        "coverage_probability_valid": bool(np.all((coverage_curve(nf10_samples, [-10, 0, 10]) >= 0.0) & (coverage_curve(nf10_samples, [-10, 0, 10]) <= 1.0))),
    }
