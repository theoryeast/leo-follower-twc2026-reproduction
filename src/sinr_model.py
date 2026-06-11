"""Physically closed SINR model for dense follower-based LEO clusters.

The default resource model is intra-cluster orthogonal access: one leader
resource block and one block per follower share a fixed ground-link bandwidth.
Other clusters reuse the same block pattern.  This avoids simultaneously
counting every serving branch as a full-band desired stream while also treating
all of those streams as cochannel interference.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import math
from typing import Iterable

import numpy as np
from scipy.special import gammaincc, roots_genlaguerre

from src.leo_follower_model import (
    SystemParams,
    db_to_linear,
    expected_log2_gamma,
    r_fu,
    r_lf,
    r_su,
    sample_fading,
    sample_psi_cap,
    sr_gamma_parameters,
    xi_fu,
    xi_lf,
    xi_lu,
)


@dataclass(frozen=True)
class SinrParams:
    trials: int = 2000
    seed: int = 20260610
    resource_model: str = "orthogonal"
    interference_method: str = "moment_gamma"
    reuse_factor: int = 1
    activity_probability: float = 1.0
    interference_gain_db: float = 0.0
    gamma_lf_db: float = -5.0
    leader_bandwidth_fraction: float | None = None
    power_model: str = "per_satellite"
    cluster_power_dbw: float = 20.0
    leader_power_fraction: float = 0.5
    follower_availability_probability: float = 1.0
    shared_reuse_color: bool = False
    isl_duplex_factor: float = 1.0
    bandwidth_scaled_noise: bool = False
    leader_chunk: int = 192
    moment_grid_size: int = 56

    def with_updates(self, **kwargs) -> "SinrParams":
        return replace(self, **kwargs)

    @property
    def thinning_probability(self) -> float:
        return min(max(self.activity_probability / max(self.reuse_factor, 1), 0.0), 1.0)

    @property
    def follower_thinning_probability(self) -> float:
        return self.thinning_probability * min(max(self.follower_availability_probability, 0.0), 1.0)

    @property
    def interference_gain_linear(self) -> float:
        return db_to_linear(self.interference_gain_db)


def scenario_params(name: str, **kwargs) -> SinrParams:
    scenarios = {
        "orthogonal_full_reuse": SinrParams(resource_model="orthogonal", reuse_factor=1, activity_probability=1.0, interference_gain_db=0.0),
        "coordinated": SinrParams(resource_model="orthogonal", reuse_factor=3, activity_probability=0.5, interference_gain_db=-20.0),
        "full_reuse_sic": SinrParams(resource_model="full_reuse_sic", reuse_factor=1, activity_probability=1.0, interference_gain_db=0.0),
        "noise_limited": SinrParams(resource_model="noise_limited", reuse_factor=1, activity_probability=0.0, interference_gain_db=-300.0),
    }
    if name not in scenarios:
        raise ValueError(f"unknown SINR scenario: {name}")
    return scenarios[name].with_updates(**kwargs)


def confidence_interval(values: np.ndarray) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    mean = float(np.mean(values))
    if values.size < 2:
        return mean, mean, mean
    half = 1.959963984540054 * float(np.std(values, ddof=1)) / math.sqrt(values.size)
    return mean, mean - half, mean + half


def binomial_confidence_interval(successes: int, trials: int) -> tuple[float, float, float]:
    """Wilson 95% interval, including well-defined limits for zero successes."""
    if trials <= 0:
        return float("nan"), float("nan"), float("nan")
    z = 1.959963984540054
    phat = successes / trials
    denom = 1.0 + z * z / trials
    center = (phat + z * z / (2.0 * trials)) / denom
    half = z * math.sqrt(phat * (1.0 - phat) / trials + z * z / (4.0 * trials * trials)) / denom
    return phat, max(0.0, center - half), min(1.0, center + half)


def _sample_serving_theta(size: int, p: SystemParams, rng: np.random.Generator) -> np.ndarray:
    """Sample nearest-leader angle conditioned on at least one visible leader."""
    p_visible = 1.0 - ((1.0 + math.cos(p.theta_max_rad)) / 2.0) ** p.n_leaders
    u = rng.random(size) * p_visible
    cos_theta = 2.0 * (1.0 - u) ** (1.0 / p.n_leaders) - 1.0
    return np.arccos(np.clip(cos_theta, math.cos(p.theta_max_rad), 1.0))


def _sample_other_theta(theta0: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    u = rng.random((theta0.size, count))
    cos_theta = -1.0 + u * (np.cos(theta0)[:, None] + 1.0)
    return np.arccos(np.clip(cos_theta, -1.0, 1.0))


def _follower_contact_cos(theta: np.ndarray, psi: np.ndarray, phi: np.ndarray) -> np.ndarray:
    return np.sin(theta) * np.sin(psi) * np.cos(phi) + np.cos(theta) * np.cos(psi)


def _active_mask(shape: tuple[int, ...], sp: SinrParams, rng: np.random.Generator) -> np.ndarray:
    return _probability_mask(shape, sp.thinning_probability, rng)


def _probability_mask(shape: tuple[int, ...], probability: float, rng: np.random.Generator) -> np.ndarray:
    probability = min(max(probability, 0.0), 1.0)
    if probability >= 1.0:
        return np.ones(shape, dtype=bool)
    if probability <= 0.0:
        return np.zeros(shape, dtype=bool)
    return rng.random(shape) < probability


def _branch_activity_mask(
    shape: tuple[int, ...],
    sp: SinrParams,
    rng: np.random.Generator,
    common_reuse: np.ndarray | None = None,
) -> np.ndarray:
    if common_reuse is None:
        return _active_mask(shape, sp, rng)
    return common_reuse & _probability_mask(shape, sp.activity_probability, rng)


def _exact_orthogonal_interference(
    p: SystemParams,
    sp: SinrParams,
    theta0: np.ndarray,
    branch_count: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact interference with shared external-cluster geometry across all RBs."""
    leader_out = np.zeros(theta0.size)
    follower_out = np.zeros((theta0.size, branch_count))
    n_other = max(p.n_leaders - 1, 0)
    gain = sp.interference_gain_linear
    for start in range(0, n_other, sp.leader_chunk):
        count = min(sp.leader_chunk, n_other - start)
        theta = _sample_other_theta(theta0, count, rng)
        common_reuse = None
        if sp.shared_reuse_color:
            common_reuse = _probability_mask(theta.shape, 1.0 / max(sp.reuse_factor, 1), rng)
        leader_visible = theta <= p.theta_max_rad
        leader_active = _branch_activity_mask(theta.shape, sp, rng, common_reuse)
        leader_fading = sample_fading(theta.shape, p, rng)
        leader_out += np.sum(
            leader_visible * leader_active * gain * xi_lu(p) * leader_fading / (r_su(theta, p) ** 2),
            axis=1,
        )
        for branch in range(branch_count):
            psi = sample_psi_cap(theta.shape, p, rng)
            phi = rng.uniform(0.0, 2.0 * math.pi, size=theta.shape)
            visible = _follower_contact_cos(theta, psi, phi) >= math.cos(p.theta_max_rad)
            available = _probability_mask(theta.shape, sp.follower_availability_probability, rng)
            active = available & _branch_activity_mask(theta.shape, sp, rng, common_reuse)
            w = sample_fading(theta.shape, p, rng)
            follower_out[:, branch] += np.sum(
                visible * active * gain * xi_fu(p) * w / (r_fu(theta, psi, phi, p) ** 2),
                axis=1,
            )
    return leader_out, follower_out


def _exact_full_reuse_interference(p: SystemParams, sp: SinrParams, theta0: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Full-band external interference with perfect serving-cluster SIC."""
    out = np.zeros(theta0.size)
    n_other = max(p.n_leaders - 1, 0)
    gain = sp.interference_gain_linear
    for start in range(0, n_other, sp.leader_chunk):
        count = min(sp.leader_chunk, n_other - start)
        theta = _sample_other_theta(theta0, count, rng)
        common_reuse = None
        if sp.shared_reuse_color:
            common_reuse = _probability_mask(theta.shape, 1.0 / max(sp.reuse_factor, 1), rng)
        leader_visible = theta <= p.theta_max_rad
        leader_active = _branch_activity_mask(theta.shape, sp, rng, common_reuse)
        leader_fading = sample_fading(theta.shape, p, rng)
        out += np.sum(
            leader_visible * leader_active * gain * xi_lu(p) * leader_fading / (r_su(theta, p) ** 2),
            axis=1,
        )
        for _ in range(p.n_followers):
            psi = sample_psi_cap(theta.shape, p, rng)
            phi = rng.uniform(0.0, 2.0 * math.pi, size=theta.shape)
            visible = _follower_contact_cos(theta, psi, phi) >= math.cos(p.theta_max_rad)
            available = _probability_mask(theta.shape, sp.follower_availability_probability, rng)
            active = available & _branch_activity_mask(theta.shape, sp, rng, common_reuse)
            w = sample_fading(theta.shape, p, rng)
            out += np.sum(visible * active * gain * xi_fu(p) * w / (r_fu(theta, psi, phi, p) ** 2), axis=1)
    return out


def _fading_moments(p: SystemParams) -> tuple[float, float]:
    shape, scale = sr_gamma_parameters(p)
    return shape * scale, shape * (shape + 1.0) * scale * scale


@lru_cache(maxsize=128)
def _conditional_moment_table(
    p: SystemParams,
    sp: SinrParams,
    branch: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Aggregate conditional mean/variance for one reused resource block."""
    n0 = sp.moment_grid_size
    theta0_grid = np.linspace(0.0, p.theta_max_rad, n0)
    means = np.zeros(n0)
    variances = np.zeros(n0)
    ew, ew2 = _fading_moments(p)
    q = sp.thinning_probability if branch == "leader" else sp.follower_thinning_probability
    g = sp.interference_gain_linear
    n_other = max(p.n_leaders - 1, 0)
    xt, wt = np.polynomial.legendre.leggauss(64)
    xp, wp = np.polynomial.legendre.leggauss(14)
    xf, wf = np.polynomial.legendre.leggauss(18)
    psi = 0.5 * p.theta_cap_rad * (xp + 1.0)
    wpsi = 0.5 * p.theta_cap_rad * wp
    phi = math.pi * (xf + 1.0)
    wphi = math.pi * wf
    psi_grid = psi[:, None]
    phi_grid = phi[None, :]
    cap_weights = wpsi[:, None] * wphi[None, :] * np.sin(psi_grid)
    cap_weights /= 2.0 * math.pi * (1.0 - math.cos(p.theta_cap_rad))

    for idx, theta0 in enumerate(theta0_grid):
        end = p.theta_max_rad if branch == "leader" else min(math.pi, p.theta_max_rad + p.theta_cap_rad)
        if theta0 >= end or n_other == 0 or q == 0.0:
            continue
        theta = 0.5 * (end - theta0) * (xt + 1.0) + theta0
        wtheta = 0.5 * (end - theta0) * wt
        cond = np.sin(theta) / (1.0 + math.cos(theta0))
        if branch == "leader":
            inv2 = 1.0 / (r_su(theta, p) ** 2)
            a1 = float(np.sum(wtheta * cond * inv2))
            a2 = float(np.sum(wtheta * cond * inv2**2))
            coeff = g * xi_lu(p)
        elif branch == "follower":
            a1 = 0.0
            a2 = 0.0
            for th, ww in zip(theta, wtheta * cond):
                visible = _follower_contact_cos(th, psi_grid, phi_grid) >= math.cos(p.theta_max_rad)
                inv2 = 1.0 / (r_fu(th, psi_grid, phi_grid, p) ** 2)
                a1 += ww * float(np.sum(cap_weights * visible * inv2))
                a2 += ww * float(np.sum(cap_weights * visible * inv2**2))
            coeff = g * xi_fu(p)
        else:
            raise ValueError(f"unknown branch: {branch}")
        m1 = q * coeff * ew * a1
        m2 = q * coeff * coeff * ew2 * a2
        means[idx] = n_other * m1
        variances[idx] = max(n_other * (m2 - m1 * m1), 0.0)
    return theta0_grid, means, variances


def conditional_interference_moments(
    p: SystemParams,
    sp: SinrParams,
    theta0: np.ndarray,
    branch: str,
) -> tuple[np.ndarray, np.ndarray]:
    # Only these fields enter the conditional interference moments.  Excluding
    # seeds, trial counts, duplex settings, and rate-allocation fields lets
    # independent validation runs reuse the same deterministic quadrature table.
    moment_sp = SinrParams(
        reuse_factor=sp.reuse_factor,
        activity_probability=sp.activity_probability,
        interference_gain_db=sp.interference_gain_db,
        follower_availability_probability=sp.follower_availability_probability,
        moment_grid_size=sp.moment_grid_size,
    )
    grid, means, variances = _conditional_moment_table(p, moment_sp, branch)
    return np.interp(theta0, grid, means), np.interp(theta0, grid, variances)


def _sample_moment_gamma(mu: np.ndarray, var: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    mu = np.asarray(mu, dtype=float)
    var = np.asarray(var, dtype=float)
    out = np.zeros_like(mu)
    mask = (mu > 0.0) & (var > 0.0)
    shape = np.divide(mu * mu, var, out=np.ones_like(mu), where=mask)
    scale = np.divide(var, mu, out=np.zeros_like(mu), where=mask)
    out[mask] = rng.gamma(shape[mask], scale[mask])
    out[(mu > 0.0) & ~mask] = mu[(mu > 0.0) & ~mask]
    return out


def _ground_branch_bandwidths(p: SystemParams, sp: SinrParams) -> tuple[float, float]:
    if sp.resource_model == "orthogonal":
        # A frequency reuse factor K gives each cluster one of K sub-bands.
        # The remaining per-cluster band is then shared by leader/follower RBs.
        reuse = max(sp.reuse_factor, 1)
        if p.n_followers == 0:
            return p.bandwidth_lu_hz / reuse, 0.0
        if sp.leader_bandwidth_fraction is None:
            share = p.n_followers + 1
            return p.bandwidth_lu_hz / (share * reuse), p.bandwidth_fu_hz / (share * reuse)
        alpha = min(max(sp.leader_bandwidth_fraction, 0.0), 1.0)
        return (
            alpha * p.bandwidth_lu_hz / reuse,
            (1.0 - alpha) * p.bandwidth_fu_hz / (p.n_followers * reuse),
        )
    return p.bandwidth_lu_hz, p.bandwidth_fu_hz


def _ground_branch_noise_scales(p: SystemParams, sp: SinrParams) -> tuple[float, float]:
    """Return branch noise powers normalized by the reference-band noise powers."""
    if not sp.bandwidth_scaled_noise:
        return 1.0, 1.0
    bw_l, bw_f = _ground_branch_bandwidths(p, sp)
    noise_l = bw_l / max(p.bandwidth_lu_hz, 1e-30)
    noise_f = 1.0 if p.n_followers == 0 else bw_f / max(p.bandwidth_fu_hz, 1e-30)
    return max(noise_l, 1e-15), max(noise_f, 1e-15)


def effective_system_params(p: SystemParams, sp: SinrParams) -> SystemParams:
    """Apply the selected ground-link power-consistency model."""
    if sp.power_model == "per_satellite":
        return p
    if sp.power_model != "fixed_cluster_total":
        raise ValueError(f"unknown power model: {sp.power_model}")
    total_w = 10.0 ** (sp.cluster_power_dbw / 10.0)
    if p.n_followers == 0:
        leader_w = total_w
        follower_w = total_w
    else:
        alpha = min(max(sp.leader_power_fraction, 0.0), 1.0)
        leader_w = max(alpha * total_w, 1e-15)
        follower_w = max((1.0 - alpha) * total_w / p.n_followers, 1e-15)
    return p.with_updates(
        rho_lu_dbw=10.0 * math.log10(leader_w),
        rho_fu_dbw=10.0 * math.log10(follower_w),
    )


def simulate_sinr_samples(p: SystemParams, sp: SinrParams | None = None) -> dict[str, np.ndarray]:
    sp = scenario_params("orthogonal_full_reuse") if sp is None else sp
    rng = np.random.default_rng(sp.seed + 101 * p.n_leaders + 17 * p.n_followers)
    p_eff = effective_system_params(p, sp)
    theta0 = _sample_serving_theta(sp.trials, p_eff, rng)
    nf = p.n_followers

    if sp.resource_model == "noise_limited":
        i_l = np.zeros(sp.trials)
        i_f = np.zeros((sp.trials, nf))
    elif sp.resource_model == "orthogonal":
        if sp.interference_method == "exact":
            i_l, i_f = _exact_orthogonal_interference(p_eff, sp, theta0, nf, rng)
        elif sp.interference_method == "moment_gamma":
            mu_l, var_l = conditional_interference_moments(p_eff, sp, theta0, "leader")
            i_l = _sample_moment_gamma(mu_l, var_l, rng)
            if nf:
                mu_f, var_f = conditional_interference_moments(p_eff, sp, theta0, "follower")
                i_f = np.column_stack([_sample_moment_gamma(mu_f, var_f, rng) for _ in range(nf)])
            else:
                i_f = np.zeros((sp.trials, 0))
        else:
            raise ValueError(f"unknown interference method: {sp.interference_method}")
    elif sp.resource_model == "full_reuse_sic":
        common = _exact_full_reuse_interference(p_eff, sp.with_updates(interference_method="exact"), theta0, rng)
        i_l = common
        i_f = np.repeat(common[:, None], nf, axis=1)
    else:
        raise ValueError(f"unknown resource model: {sp.resource_model}")

    w_l = sample_fading(sp.trials, p_eff, rng)
    desired_l = xi_lu(p_eff) * w_l / (r_su(theta0, p_eff) ** 2)
    bw_l, bw_f = _ground_branch_bandwidths(p_eff, sp)
    noise_l, noise_f = _ground_branch_noise_scales(p_eff, sp)
    sinr_l = desired_l / (noise_l + i_l)
    rate_l = bw_l * np.log2(1.0 + sinr_l)

    if nf:
        psi = sample_psi_cap((sp.trials, nf), p_eff, rng)
        phi = rng.uniform(0.0, 2.0 * math.pi, size=(sp.trials, nf))
        visible_f = _follower_contact_cos(theta0[:, None], psi, phi) >= math.cos(p_eff.theta_max_rad)
        available_f = _probability_mask((sp.trials, nf), sp.follower_availability_probability, rng)
        w_f = sample_fading((sp.trials, nf), p_eff, rng)
        desired_f = (
            available_f
            * visible_f
            * xi_fu(p_eff)
            * w_f
            / (r_fu(theta0[:, None], psi, phi, p_eff) ** 2)
        )
        sinr_f = desired_f / (noise_f + i_f)
        snr_lf = available_f * xi_lf(p_eff) / (r_lf(psi, p_eff) ** 2)
        rate_f = bw_f * np.log2(1.0 + sinr_f)
        rate_lf = p_eff.bandwidth_lf_hz * np.log2(1.0 + snr_lf)
        relay_rate = sp.isl_duplex_factor * np.minimum(rate_lf, rate_f)
        cluster_rate = rate_l + np.sum(relay_rate, axis=1)
        access_best = np.maximum(sinr_l, np.max(sinr_f, axis=1))
        e2e_success_matrix = (sinr_f >= p.gamma_th_linear) & (snr_lf >= db_to_linear(sp.gamma_lf_db))
        e2e_coverage = (sinr_l >= p.gamma_th_linear) | np.any(e2e_success_matrix, axis=1)
    else:
        psi = np.zeros((sp.trials, 0))
        sinr_f = np.zeros((sp.trials, 0))
        desired_f = np.zeros((sp.trials, 0))
        snr_lf = np.zeros((sp.trials, 0))
        rate_f = np.zeros((sp.trials, 0))
        rate_lf = np.zeros((sp.trials, 0))
        relay_rate = np.zeros((sp.trials, 0))
        cluster_rate = rate_l
        access_best = sinr_l
        e2e_coverage = sinr_l >= p.gamma_th_linear

    return {
        "theta0": theta0,
        "i_leader_rb": i_l,
        "i_follower_rb": i_f,
        "desired_lu_normalized": desired_l,
        "desired_fu_normalized": desired_f,
        "noise_scale_lu": np.array([noise_l], dtype=float),
        "noise_scale_fu": np.array([noise_f], dtype=float),
        "sinr_lu": sinr_l,
        "sinr_fu": sinr_f,
        "snr_lf": snr_lf,
        "sinr_access_best": access_best,
        "coverage_e2e_default": e2e_coverage,
        "gamma_th_db": np.array([p_eff.gamma_th_db], dtype=float),
        "gamma_lf_db": np.array([sp.gamma_lf_db], dtype=float),
        "rate_lu_bps": rate_l,
        "rate_fu_bps": rate_f,
        "rate_lf_bps": rate_lf,
        "rate_relay_bps": relay_rate,
        "cluster_rate_bps": cluster_rate,
        "effective_rho_lu_dbw": np.array([p_eff.rho_lu_dbw], dtype=float),
        "effective_rho_fu_dbw": np.array([p_eff.rho_fu_dbw], dtype=float),
    }


def access_coverage_curve(samples: dict[str, np.ndarray], thresholds_db: Iterable[float]) -> np.ndarray:
    best = samples["sinr_access_best"]
    return np.array([np.mean(best >= db_to_linear(t)) for t in thresholds_db], dtype=float)


def end_to_end_coverage_curve(
    samples: dict[str, np.ndarray],
    thresholds_db: Iterable[float],
    gamma_lf_db: float | None = None,
) -> np.ndarray:
    sinr_l = samples["sinr_lu"]
    sinr_f = samples["sinr_fu"]
    snr_lf = samples["snr_lf"]
    if gamma_lf_db is None:
        gamma_lf_db = float(samples.get("gamma_lf_db", np.array([-5.0]))[0])
    out = []
    for t in thresholds_db:
        th = db_to_linear(t)
        if sinr_f.shape[1]:
            success = (sinr_l >= th) | np.any((sinr_f >= th) & (snr_lf >= db_to_linear(gamma_lf_db)), axis=1)
        else:
            success = sinr_l >= th
        out.append(np.mean(success))
    return np.array(out, dtype=float)


def summarize_sinr_samples(samples: dict[str, np.ndarray]) -> dict[str, float]:
    rate, rate_lo, rate_hi = confidence_interval(samples["cluster_rate_bps"])
    i_l, i_l_lo, i_l_hi = confidence_interval(samples["i_leader_rb"])
    rates = np.asarray(samples["cluster_rate_bps"], dtype=float)
    return {
        "mean_rate_gbps": rate / 1e9,
        "rate_ci_low_gbps": rate_lo / 1e9,
        "rate_ci_high_gbps": rate_hi / 1e9,
        "rate_p05_gbps": float(np.quantile(rates, 0.05)) / 1e9,
        "rate_median_gbps": float(np.quantile(rates, 0.50)) / 1e9,
        "rate_p95_gbps": float(np.quantile(rates, 0.95)) / 1e9,
        "mean_leader_rb_inr": i_l,
        "leader_rb_inr_ci_low": i_l_lo,
        "leader_rb_inr_ci_high": i_l_hi,
        "default_e2e_coverage": float(np.mean(samples["coverage_e2e_default"])),
        "default_access_coverage": float(
            np.mean(samples["sinr_access_best"] >= db_to_linear(float(samples.get("gamma_th_db", np.array([-5.0]))[0])))
        ),
    }


def estimate_boundary_follower_interference_fraction(
    p: SystemParams,
    samples: int = 250_000,
    seed: int = 20260611,
) -> float:
    """Fraction of mean follower interference missed by requiring its leader visible."""
    rng = np.random.default_rng(seed + p.n_leaders)
    theta0 = _sample_serving_theta(samples, p, rng)
    theta = _sample_other_theta(theta0, 1, rng)[:, 0]
    psi = sample_psi_cap(samples, p, rng)
    phi = rng.uniform(0.0, 2.0 * math.pi, size=samples)
    visible_f = _follower_contact_cos(theta, psi, phi) >= math.cos(p.theta_max_rad)
    visible_l = theta <= p.theta_max_rad
    power = visible_f * (1.0 / (r_fu(theta, psi, phi, p) ** 2))
    total = float(np.mean(power))
    boundary = float(np.mean(power * ~visible_l))
    return boundary / max(total, 1e-300)


def semi_analytical_leader_metrics(
    p: SystemParams,
    sp: SinrParams,
    thresholds_db: Iterable[float],
    n_theta: int = 72,
    n_interference: int = 28,
) -> tuple[np.ndarray, float]:
    """Moment-matched semi-analytical LU coverage and rate."""
    if sp.resource_model != "orthogonal":
        raise ValueError("semi-analytical leader metrics are defined for orthogonal resources")
    x, w = np.polynomial.legendre.leggauss(n_theta)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    pvis = 1.0 - ((1.0 + math.cos(p.theta_max_rad)) / 2.0) ** p.n_leaders
    density = p.n_leaders * np.sin(theta) / 2.0 * ((1.0 + np.cos(theta)) / 2.0) ** (p.n_leaders - 1) / pvis
    mu, var = conditional_interference_moments(p, sp, theta, "leader")
    fading_shape, fading_scale = sr_gamma_parameters(p)
    thresholds = list(thresholds_db)
    cov = np.zeros(len(thresholds))
    rate_integrand = np.zeros(theta.size)
    for j, th in enumerate(theta):
        if mu[j] <= 0.0 or var[j] <= 0.0:
            i_nodes = np.array([mu[j]])
            i_weights = np.array([1.0])
        else:
            ishape = mu[j] * mu[j] / var[j]
            iscale = var[j] / mu[j]
            nodes, weights = roots_genlaguerre(n_interference, ishape - 1.0)
            i_nodes = iscale * nodes
            i_weights = weights / math.gamma(ishape)
        for idx, threshold_db in enumerate(thresholds):
            arg = db_to_linear(threshold_db) * (1.0 + i_nodes) * r_su(th, p) ** 2 / xi_lu(p)
            cov[idx] += wtheta[j] * density[j] * float(np.sum(i_weights * gammaincc(fading_shape, arg / fading_scale)))
        a = xi_lu(p) / ((1.0 + i_nodes) * r_su(th, p) ** 2)
        rate_integrand[j] = float(np.sum(i_weights * expected_log2_gamma(a, p)))
    bw_l, _ = _ground_branch_bandwidths(p, sp)
    rate = float(bw_l * np.sum(wtheta * density * rate_integrand))
    return cov, rate


def run_sinr_validation() -> dict[str, object]:
    checks: dict[str, object] = {}
    p = SystemParams(n_leaders=900, n_followers=10)
    noise = simulate_sinr_samples(p, scenario_params("noise_limited", trials=4000, seed=1))
    orth = simulate_sinr_samples(p, scenario_params("orthogonal_full_reuse", trials=2200, seed=2))
    coord = simulate_sinr_samples(p, scenario_params("coordinated", trials=2200, seed=3))
    exact = simulate_sinr_samples(p.with_updates(n_followers=5), scenario_params("orthogonal_full_reuse", trials=1000, seed=4, interference_method="exact"))
    gamma = simulate_sinr_samples(p.with_updates(n_followers=5), scenario_params("orthogonal_full_reuse", trials=4000, seed=5, interference_method="moment_gamma"))
    thresholds = [-20.0, -15.0, -10.0]
    semi_cov, semi_rate = semi_analytical_leader_metrics(p, scenario_params("orthogonal_full_reuse"), thresholds)
    mc_lu_cov = np.array([np.mean(orth["sinr_lu"] >= db_to_linear(t)) for t in thresholds])
    checks["finite_outputs"] = bool(all(np.all(np.isfinite(v)) for v in [noise["cluster_rate_bps"], orth["cluster_rate_bps"], coord["cluster_rate_bps"]]))
    checks["coverage_ranges_valid"] = bool(np.all((access_coverage_curve(orth, thresholds) >= 0.0) & (access_coverage_curve(orth, thresholds) <= 1.0)))
    checks["e2e_not_above_access"] = bool(np.all(end_to_end_coverage_curve(orth, thresholds) <= access_coverage_curve(orth, thresholds) + 1e-12))
    checks["coordinated_improves_default_e2e"] = bool(np.mean(coord["coverage_e2e_default"]) >= np.mean(orth["coverage_e2e_default"]))
    checks["noise_limited_has_zero_interference"] = bool(np.max(noise["i_leader_rb"]) == 0.0)
    bw1_l, bw1_f = _ground_branch_bandwidths(p, scenario_params("orthogonal_full_reuse"))
    bw3_l, bw3_f = _ground_branch_bandwidths(p, scenario_params("coordinated"))
    bw1 = bw1_l + p.n_followers * bw1_f
    bw3 = bw3_l + p.n_followers * bw3_f
    checks["reuse_bandwidth_cost_applied"] = bool(math.isclose(bw3, bw1 / 3.0, rel_tol=1e-12))
    checks["gamma_vs_exact_rate_relative_error"] = abs(np.mean(gamma["cluster_rate_bps"]) - np.mean(exact["cluster_rate_bps"])) / np.mean(exact["cluster_rate_bps"])
    checks["gamma_vs_exact_e2e_coverage_abs_error"] = abs(
        np.mean(gamma["coverage_e2e_default"]) - np.mean(exact["coverage_e2e_default"])
    )
    checks["semi_vs_mc_lu_coverage_max_abs_error"] = float(np.max(np.abs(semi_cov - mc_lu_cov)))
    checks["semi_lu_rate_gbps"] = semi_rate / 1e9
    checks["mc_lu_rate_gbps"] = float(np.mean(orth["rate_lu_bps"]) / 1e9)
    checks["boundary_follower_interference_fraction_nl900"] = estimate_boundary_follower_interference_fraction(p, samples=120_000)
    checks["all_acceptance_checks_pass"] = bool(
        checks["finite_outputs"]
        and checks["coverage_ranges_valid"]
        and checks["e2e_not_above_access"]
        and checks["coordinated_improves_default_e2e"]
        and checks["noise_limited_has_zero_interference"]
        and checks["reuse_bandwidth_cost_applied"]
        and checks["gamma_vs_exact_rate_relative_error"] < 0.03
        and checks["gamma_vs_exact_e2e_coverage_abs_error"] < 0.05
        and checks["semi_vs_mc_lu_coverage_max_abs_error"] < 0.04
        and checks["boundary_follower_interference_fraction_nl900"] > 0.0
    )
    return checks
