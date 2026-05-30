"""Analytical and simulation helpers for Ru/Wang/Alouini TWC 2026.

The code follows the notation of:
Coverage and Rate Analysis of Follower-Based LEO Satellite Networks:
A Stochastic Geometry Approach, IEEE TWC, 2026.

All distances are SI units and all powers are linear watts unless a helper
explicitly says dB/dBW/dBm.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import math
from typing import Iterable

import numpy as np
from scipy.integrate import quad
from scipy.special import gammainc, gamma as gamma_fn, roots_genlaguerre


def db_to_linear(value_db: float) -> float:
    return 10.0 ** (value_db / 10.0)


def dbw_to_watt(value_dbw: float) -> float:
    return 10.0 ** (value_dbw / 10.0)


def dbm_to_watt(value_dbm: float) -> float:
    return 10.0 ** ((value_dbm - 30.0) / 10.0)


@dataclass(frozen=True)
class SystemParams:
    earth_radius_m: float = 6371e3
    altitude_m: float = 600e3
    n_leaders: int = 1000
    n_followers: int = 10
    theta_cap_rad: float = math.radians(1.0)
    theta_max_rad: float = math.pi / 4.0
    gamma_th_db: float = -5.0
    rho_lu_dbw: float = 20.0
    rho_fu_dbw: float = 15.0
    rho_lf_dbw: float = 5.0
    gain_lu_dbi: float = 30.0
    gain_fu_dbi: float = 30.0
    gain_lf_dbi: float = 30.0
    wavelength_lu_m: float = 0.015
    wavelength_fu_m: float = 0.015
    wavelength_lf_m: float = 0.015
    zeta_u_db: float = -2.0
    zeta_f_db: float = 0.0
    noise_u_dbm: float = -94.0
    noise_f_dbm: float = -84.0
    omega: float = 1.29
    b0: float = 0.158
    m: float = 19.4
    # The paper's Table I omits B. 100 MHz matches the plotted Gbps scale.
    bandwidth_lu_hz: float = 100e6
    bandwidth_fu_hz: float = 100e6
    bandwidth_lf_hz: float = 100e6

    @property
    def satellite_radius_m(self) -> float:
        return self.earth_radius_m + self.altitude_m

    @property
    def gamma_th_linear(self) -> float:
        return db_to_linear(self.gamma_th_db)

    def with_updates(self, **kwargs) -> "SystemParams":
        return replace(self, **kwargs)


def sr_gamma_parameters(p: SystemParams) -> tuple[float, float]:
    """Return the gamma approximation shape and scale from Eq. (9)-(10)."""
    omega, b0, m = p.omega, p.b0, p.m
    denom = 4.0 * m * b0 * b0 + 4.0 * m * b0 * omega + omega * omega
    shape = m * (2.0 * b0 + omega) ** 2 / denom
    scale = denom / (m * (2.0 * b0 + omega))
    return shape, scale


def sr_cdf_gamma_approx(w: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    shape, scale = sr_gamma_parameters(p)
    return gammainc(shape, np.asarray(w) / scale)


def xi_lu(p: SystemParams) -> float:
    return (
        dbw_to_watt(p.rho_lu_dbw)
        * db_to_linear(p.gain_lu_dbi)
        * db_to_linear(p.zeta_u_db)
        * (p.wavelength_lu_m / (4.0 * math.pi)) ** 2
        / dbm_to_watt(p.noise_u_dbm)
    )


def xi_fu(p: SystemParams) -> float:
    return (
        dbw_to_watt(p.rho_fu_dbw)
        * db_to_linear(p.gain_fu_dbi)
        * db_to_linear(p.zeta_u_db)
        * (p.wavelength_fu_m / (4.0 * math.pi)) ** 2
        / dbm_to_watt(p.noise_u_dbm)
    )


def xi_lf(p: SystemParams) -> float:
    return (
        dbw_to_watt(p.rho_lf_dbw)
        * db_to_linear(p.gain_lf_dbi)
        * db_to_linear(p.zeta_f_db)
        * (p.wavelength_lf_m / (4.0 * math.pi)) ** 2
        / dbm_to_watt(p.noise_f_dbm)
    )


def r_su(theta: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    re = p.earth_radius_m
    rs = p.satellite_radius_m
    theta_arr = np.asarray(theta)
    val = np.sqrt(re * re + rs * rs - 2.0 * re * rs * np.cos(theta_arr))
    if np.isscalar(theta):
        return float(val)
    return val


def r_lf(psi: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    val = p.satellite_radius_m * np.sqrt(2.0 * (1.0 - np.cos(psi)))
    if np.isscalar(psi):
        return float(val)
    return val


def r_fu(theta: np.ndarray, psi: np.ndarray, phi: np.ndarray, p: SystemParams) -> np.ndarray:
    re = p.earth_radius_m
    rs = p.satellite_radius_m
    cos_contact = np.sin(theta) * np.sin(psi) * np.cos(phi) + np.cos(theta) * np.cos(psi)
    return np.sqrt(re * re + rs * rs - 2.0 * re * rs * cos_contact)


def f_theta_lu(theta: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    nl = p.n_leaders
    theta_arr = np.asarray(theta)
    val = nl * np.sin(theta_arr) / 2.0 * ((1.0 + np.cos(theta_arr)) / 2.0) ** (nl - 1)
    if np.isscalar(theta):
        return float(val)
    return val


def f_theta_fu_min(theta: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    nl = p.n_leaders
    theta_arr = np.asarray(theta)
    t = theta_arr + p.theta_cap_rad
    val = nl * np.sin(t) / 2.0 * ((1.0 + np.cos(t)) / 2.0) ** (nl - 1)
    val = np.where((theta_arr > 0.0) & (theta_arr <= p.theta_max_rad - p.theta_cap_rad), val, 0.0)
    if np.isscalar(theta):
        return float(val)
    return val


def f_theta_fu_max(theta: np.ndarray | float, p: SystemParams) -> np.ndarray | float:
    nl = p.n_leaders
    theta_arr = np.asarray(theta)
    t = theta_arr - p.theta_cap_rad
    val = nl * np.sin(t) / 2.0 * ((1.0 + np.cos(t)) / 2.0) ** (nl - 1)
    val = np.where((theta_arr >= p.theta_cap_rad) & (theta_arr <= p.theta_max_rad + p.theta_cap_rad), val, 0.0)
    if np.isscalar(theta):
        return float(val)
    return val


@lru_cache(maxsize=16)
def _unit_quad_nodes(n_theta: int, n_psi: int, n_phi: int) -> tuple[np.ndarray, ...]:
    x_t, w_t = np.polynomial.legendre.leggauss(n_theta)
    x_p, w_p = np.polynomial.legendre.leggauss(n_psi)
    x_f, w_f = np.polynomial.legendre.leggauss(n_phi)
    return x_t, w_t, x_p, w_p, x_f, w_f


def outage_leader(gamma_linear: float, p: SystemParams) -> float:
    x_lu = xi_lu(p)

    def integrand(theta: float) -> float:
        arg = gamma_linear * r_su(theta, p) ** 2 / x_lu
        return float(sr_cdf_gamma_approx(arg, p)) * f_theta_lu(theta, p)

    val, _ = quad(integrand, 0.0, p.theta_max_rad, epsabs=1e-9, epsrel=1e-7, limit=250)
    return min(max(val, 0.0), 1.0)


def outage_follower_conditional(
    theta: np.ndarray | float,
    gamma_linear: float,
    p: SystemParams,
    n_psi: int = 32,
    n_phi: int = 48,
) -> np.ndarray | float:
    """Eq. (20), evaluated by tensor Gauss-Legendre quadrature."""
    theta_arr = np.atleast_1d(np.asarray(theta, dtype=float))
    x_p, w_p = np.polynomial.legendre.leggauss(n_psi)
    x_f, w_f = np.polynomial.legendre.leggauss(n_phi)
    psi = 0.5 * p.theta_cap_rad * (x_p + 1.0)
    wpsi = 0.5 * p.theta_cap_rad * w_p
    phi = math.pi * (x_f + 1.0)
    wphi = math.pi * w_f
    psi_grid = psi[None, :, None]
    phi_grid = phi[None, None, :]
    weights = wpsi[None, :, None] * wphi[None, None, :] * np.sin(psi_grid)
    weights = weights / (2.0 * math.pi * (1.0 - math.cos(p.theta_cap_rad)))
    dist = r_fu(theta_arr[:, None, None], psi_grid, phi_grid, p)
    vals = sr_cdf_gamma_approx(gamma_linear * dist * dist / xi_fu(p), p)
    out = np.sum(vals * weights, axis=(1, 2))
    if np.isscalar(theta):
        return float(out[0])
    return out


def outage_cluster(
    gamma_linear: float,
    p: SystemParams,
    n_theta: int = 90,
    n_psi: int = 28,
    n_phi: int = 40,
) -> float:
    if p.n_followers <= 0:
        return outage_leader(gamma_linear, p)
    x, w = np.polynomial.legendre.leggauss(n_theta)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    p_lu = sr_cdf_gamma_approx(gamma_linear * r_su(theta, p) ** 2 / xi_lu(p), p)
    p_fu = outage_follower_conditional(theta, gamma_linear, p, n_psi=n_psi, n_phi=n_phi)
    val = np.sum(wtheta * (p_fu**p.n_followers) * p_lu * f_theta_lu(theta, p))
    return min(max(float(val), 0.0), 1.0)


def outage_cluster_bounds(gamma_linear: float, p: SystemParams, n_theta: int = 180) -> tuple[float, float]:
    """Geometric closest/farthest follower bounds used for visual QA.

    The lower curve assumes every follower is at the closest cap point to the
    user; the upper curve assumes every follower is at the farthest cap point.
    """
    if p.n_followers <= 0:
        val = outage_leader(gamma_linear, p)
        return val, val
    x, w = np.polynomial.legendre.leggauss(n_theta)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    p_lu = sr_cdf_gamma_approx(gamma_linear * r_su(theta, p) ** 2 / xi_lu(p), p)
    closest = np.maximum(theta - p.theta_cap_rad, 0.0)
    farthest = theta + p.theta_cap_rad
    p_fu_low = sr_cdf_gamma_approx(gamma_linear * r_su(closest, p) ** 2 / xi_fu(p), p)
    p_fu_high = sr_cdf_gamma_approx(gamma_linear * r_su(farthest, p) ** 2 / xi_fu(p), p)
    lower = np.sum(wtheta * (p_fu_low**p.n_followers) * p_lu * f_theta_lu(theta, p))
    upper = np.sum(wtheta * (p_fu_high**p.n_followers) * p_lu * f_theta_lu(theta, p))
    return min(max(float(lower), 0.0), 1.0), min(max(float(upper), 0.0), 1.0)


@lru_cache(maxsize=32)
def _laguerre_nodes(shape_rounded: float, n: int) -> tuple[np.ndarray, np.ndarray, float]:
    shape = shape_rounded
    x, w = roots_genlaguerre(n, shape - 1.0)
    return x, w, float(gamma_fn(shape))


def expected_log2_gamma(a: np.ndarray | float, p: SystemParams, n: int = 64) -> np.ndarray | float:
    """E[log2(1+a W)] for W approximated by Eq. (8)."""
    shape, scale = sr_gamma_parameters(p)
    # Round the cache key only; the approximation error is far below plot error.
    x, w, g = _laguerre_nodes(round(shape, 12), n)
    a_arr = np.asarray(a, dtype=float)
    vals = (w[:, None] * np.log2(1.0 + scale * x[:, None] * a_arr.ravel()[None, :])).sum(axis=0) / g
    vals = vals.reshape(a_arr.shape)
    if np.isscalar(a):
        return float(vals)
    return vals


def average_rate_leader(p: SystemParams, n_theta: int = 160) -> float:
    x, w = np.polynomial.legendre.leggauss(n_theta)
    theta = 0.5 * p.theta_max_rad * (x + 1.0)
    wtheta = 0.5 * p.theta_max_rad * w
    spectral = expected_log2_gamma(xi_lu(p) / (r_su(theta, p) ** 2), p)
    return float(p.bandwidth_lu_hz * np.sum(wtheta * spectral * f_theta_lu(theta, p)))


def average_rate_follower_bound(
    p: SystemParams,
    bound: str,
    n_theta: int = 180,
) -> float:
    """Corollary 2 upper/lower approximation in bps."""
    if p.n_followers <= 0:
        return average_rate_leader(p)
    if bound not in {"upper", "lower"}:
        raise ValueError("bound must be 'upper' or 'lower'")
    if bound == "upper":
        mass_zero = 1.0 - ((1.0 + math.cos(p.theta_cap_rad)) / 2.0) ** p.n_leaders
        a0 = xi_fu(p) / (r_su(0.0, p) ** 2)
        zero_rate = mass_zero * expected_log2_gamma(a0, p)
        end = max(p.theta_max_rad - p.theta_cap_rad, 1e-9)
        x, w = np.polynomial.legendre.leggauss(n_theta)
        theta = 0.5 * end * (x + 1.0)
        wtheta = 0.5 * end * w
        density = f_theta_fu_min(theta, p)
        spectral = expected_log2_gamma(xi_fu(p) / (r_su(theta, p) ** 2), p)
        follower_rate = p.bandwidth_fu_hz * (zero_rate + np.sum(wtheta * spectral * density))
    else:
        start = p.theta_cap_rad
        end = p.theta_max_rad + p.theta_cap_rad
        x, w = np.polynomial.legendre.leggauss(n_theta)
        theta = 0.5 * (end - start) * (x + 1.0) + start
        wtheta = 0.5 * (end - start) * w
        density = f_theta_fu_max(theta, p)
        spectral = expected_log2_gamma(xi_fu(p) / (r_su(theta, p) ** 2), p)
        follower_rate = p.bandwidth_fu_hz * np.sum(wtheta * spectral * density)
    return average_rate_leader(p) + p.n_followers * float(follower_rate)


def average_rate_cluster_middle(p: SystemParams) -> float:
    upper = average_rate_follower_bound(p, "upper")
    lower = average_rate_follower_bound(p, "lower")
    return 0.5 * (upper + lower)


def average_rate_cluster_monte_carlo(
    p: SystemParams,
    samples: int = 80_000,
    seed: int = 20260665,
) -> float:
    """Monte Carlo version of Eq. (28), using the gamma fading approximation."""
    rng = np.random.default_rng(seed)
    theta = sample_theta_lu(samples, p, rng)
    w_lu = sample_fading(samples, p, rng)
    lu_rate = p.bandwidth_lu_hz * np.log2(1.0 + xi_lu(p) * w_lu / (r_su(theta, p) ** 2))
    if p.n_followers <= 0:
        return float(np.mean(lu_rate))
    psi = sample_psi_cap((samples, p.n_followers), p, rng)
    phi = rng.uniform(0.0, 2.0 * math.pi, size=(samples, p.n_followers))
    w_fu = sample_fading((samples, p.n_followers), p, rng)
    dist_fu = r_fu(theta[:, None], psi, phi, p)
    fu_rate = p.bandwidth_fu_hz * np.log2(1.0 + xi_fu(p) * w_fu / (dist_fu**2))
    lf_rate = p.bandwidth_lf_hz * np.log2(1.0 + xi_lf(p) / (r_lf(psi, p) ** 2))
    return float(np.mean(lu_rate + np.sum(np.minimum(lf_rate, fu_rate), axis=1)))


def sample_fading(size: int | tuple[int, ...], p: SystemParams, rng: np.random.Generator) -> np.ndarray:
    shape, scale = sr_gamma_parameters(p)
    return rng.gamma(shape=shape, scale=scale, size=size)


def sample_theta_lu(size: int, p: SystemParams, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(size)
    cos_theta = 2.0 * (1.0 - u) ** (1.0 / p.n_leaders) - 1.0
    theta = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    # The probability outside theta_max is negligible for Table I, but clip to
    # the integration domain to keep rare samples from dominating diagnostics.
    return np.minimum(theta, p.theta_max_rad)


def sample_psi_cap(size: int | tuple[int, ...], p: SystemParams, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(size)
    cos_psi = 1.0 - u * (1.0 - math.cos(p.theta_cap_rad))
    return np.arccos(np.clip(cos_psi, -1.0, 1.0))


def outage_cluster_monte_carlo(
    gamma_linear: float,
    p: SystemParams,
    samples: int = 120_000,
    seed: int = 20260666,
) -> float:
    rng = np.random.default_rng(seed)
    theta = sample_theta_lu(samples, p, rng)
    w_lu = sample_fading(samples, p, rng)
    leader_out = xi_lu(p) * w_lu / (r_su(theta, p) ** 2) < gamma_linear
    if p.n_followers <= 0:
        return float(np.mean(leader_out))
    psi = sample_psi_cap((samples, p.n_followers), p, rng)
    phi = rng.uniform(0.0, 2.0 * math.pi, size=(samples, p.n_followers))
    w_fu = sample_fading((samples, p.n_followers), p, rng)
    dist = r_fu(theta[:, None], psi, phi, p)
    followers_out = xi_fu(p) * w_fu / (dist**2) < gamma_linear
    return float(np.mean(leader_out & np.all(followers_out, axis=1)))


def n_leader_sweep_values() -> np.ndarray:
    return np.array([100, 300, 450, 650, 850, 1050, 1250, 1450], dtype=int)


def run_sanity_checks() -> dict[str, float | bool]:
    p = SystemParams()
    theta_grid = np.linspace(0.0, p.theta_max_rad, 512)
    cdf_like = 1.0 - ((1.0 + np.cos(theta_grid)) / 2.0) ** p.n_leaders
    leader0 = outage_cluster(db_to_linear(-5.0), p.with_updates(n_followers=0), n_theta=50)
    direct = outage_leader(db_to_linear(-5.0), p)
    lower, upper = outage_cluster_bounds(db_to_linear(-5.0), p)
    actual = outage_cluster(db_to_linear(-5.0), p, n_theta=50, n_psi=18, n_phi=24)
    return {
        "theta_cdf_monotone": bool(np.all(np.diff(cdf_like) >= -1e-14)),
        "leader_degeneracy_abs_error": abs(leader0 - direct),
        "outage_lower": lower,
        "outage_actual": actual,
        "outage_upper": upper,
        "bounds_contain_actual": bool(lower <= actual <= upper),
        "leader_rate_gbps": average_rate_leader(p) / 1e9,
    }


def as_gbps(values: Iterable[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float) / 1e9

