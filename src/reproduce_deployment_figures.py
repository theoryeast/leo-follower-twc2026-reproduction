"""Generate deployment-optimization and consistency figures D1-D7."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deployment_optimization_model import (  # noqa: E402
    DeploymentSearch,
    cluster_rate_for_alpha,
    correlation_diagnostics,
    evaluate_samples,
    optimize_follower_count,
)
from src.leo_follower_model import SystemParams  # noqa: E402
from src.sinr_model import (  # noqa: E402
    end_to_end_coverage_curve,
    scenario_params,
    simulate_sinr_samples,
    summarize_sinr_samples,
)


FIG_DIR = ROOT / "figures" / "deployment"
DATA_DIR = ROOT / "figures" / "deployment_data"
FIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8.5,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.15,
            "lines.markersize": 4.5,
            "savefig.dpi": 300,
        }
    )


def finish(ax: plt.Axes) -> None:
    ax.grid(True, color="#888888", alpha=0.28, linewidth=0.45)
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(0.7)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def save_csv(name: str, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {name}")
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with (DATA_DIR / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def trials_for(mode: str, final: int, fast: int) -> int:
    return final if mode == "final" else fast


def fig_d1(mode: str) -> None:
    """Equal, leader-guaranteed, and rate-optimal symmetric allocation."""
    nfs = [0, 2, 5, 10, 15, 20, 30]
    alpha_grid = [0.2, 0.35, 0.5, 0.65, 0.8]
    strategies = [
        ("Equal", "blue", "o"),
        ("Leader guarantee", "#00a83b", "s"),
        (r"Rate-optimal grid ($\alpha\leq0.8$)", "red", "d"),
    ]
    rates = {name: [] for name, _, _ in strategies}
    opt_alpha: list[float] = []
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 3500, 650)
    for nf in nfs:
        p = SystemParams(n_leaders=1000, n_followers=nf)
        sp = scenario_params("coordinated", trials=n, seed=10100 + nf, bandwidth_scaled_noise=True)
        samples = simulate_sinr_samples(p, sp)
        equal = 1.0 if nf == 0 else 1.0 / (nf + 1)
        guard = 1.0 if nf == 0 else 0.5
        candidates = [1.0] if nf == 0 else sorted(set(alpha_grid + [equal, guard]))
        evaluated = [evaluate_samples(samples, p, sp, alpha) for alpha in candidates]
        best = max(evaluated, key=lambda row: row["mean_rate_gbps"])
        values = {
            "Equal": evaluate_samples(samples, p, sp, equal),
            "Leader guarantee": evaluate_samples(samples, p, sp, guard),
            r"Rate-optimal grid ($\alpha\leq0.8$)": best,
        }
        opt_alpha.append(float(best["alpha"]))
        for label, metrics in values.items():
            rates[label].append(metrics["mean_rate_gbps"])
            rows.append({"strategy": label, "n_followers": nf, **metrics})

    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True)
    for label, color, marker in strategies:
        axes[0].plot(nfs, rates[label], color=color, marker=marker, markerfacecolor="none", label=label)
    axes[0].set_xlabel("Number of Follower Satellites")
    axes[0].set_ylabel("Average Cluster Rate (Gbps)")
    axes[0].legend(frameon=True, fancybox=False, edgecolor="black")
    finish(axes[0])
    axes[1].plot(nfs, opt_alpha, "-o", color="red", markerfacecolor="none")
    axes[1].set_xlabel("Number of Follower Satellites")
    axes[1].set_ylabel(r"Grid-Optimal Leader Bandwidth Fraction $\alpha^\star$")
    axes[1].set_title("Thermal noise scales with allocated bandwidth")
    axes[1].set_ylim(0.0, 1.02)
    finish(axes[1])
    save(fig, "figD1_allocation_strategies")
    save_csv("figD1_allocation_strategies", rows)


def fig_d2(mode: str) -> None:
    """Optimal follower count curves and density-isolation phase diagram."""
    nls = [600, 900, 1200, 1500, 1800]
    n = trials_for(mode, 2200, 500)
    search = DeploymentSearch(
        coverage_target=0.99,
        conservative_constraint=True,
        independent_validation=True,
        validation_trials=trials_for(mode, 5000, 1000),
        rate_tolerance_relative=0.03,
        reselect_on_validation=True,
        exact_audit=True,
        exact_audit_trials=trials_for(mode, 3000, 700),
        exact_audit_shared_reuse_color=True,
    )
    scenarios = [
        ("K=1, -20 dB", dict(reuse_factor=1, activity_probability=0.5, interference_gain_db=-20.0), "black", "o"),
        ("K=3, -10 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-10.0), "red", "s"),
        ("K=3, -20 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-20.0), "blue", "d"),
        ("K=6, -20 dB", dict(reuse_factor=6, activity_probability=0.5, interference_gain_db=-20.0), "#00a83b", "^"),
        ("K=3, p_act=0.1", dict(reuse_factor=3, activity_probability=0.1, interference_gain_db=-20.0), "#9a4aa0", "v"),
    ]
    rows: list[dict[str, object]] = []
    curve_values: dict[str, list[float]] = {}
    for sidx, (label, kwargs, _, _) in enumerate(scenarios):
        values: list[float] = []
        for nl in nls:
            sp = scenario_params(
                "orthogonal_full_reuse",
                trials=n,
                seed=20200 + 100 * sidx + nl,
                bandwidth_scaled_noise=True,
                power_model="fixed_cluster_total",
                cluster_power_dbw=20.0,
                leader_power_fraction=0.5,
                **kwargs,
            )
            best, candidates = optimize_follower_count(nl, sp, search)
            for row in candidates:
                rows.append({"scan": "curve", "scenario": label, **row})
            values.append(np.nan if best is None else float(best["n_followers"]))
            print(
                f"[Fig.D2 curve] {label}, N_L={nl}: "
                f"N_F^dagger={'none' if best is None else int(best['n_followers'])}",
                flush=True,
            )
        curve_values[label] = values

    gains = [-25.0, -20.0, -15.0, -10.0, -5.0]
    phase = np.full((len(gains), len(nls)), np.nan)
    for i, gain in enumerate(gains):
        for j, nl in enumerate(nls):
            sp = scenario_params(
                "orthogonal_full_reuse",
                trials=n,
                seed=25200 + i * 100 + nl,
                reuse_factor=3,
                activity_probability=0.5,
                interference_gain_db=gain,
                bandwidth_scaled_noise=True,
                power_model="fixed_cluster_total",
                cluster_power_dbw=20.0,
                leader_power_fraction=0.5,
            )
            best, candidates = optimize_follower_count(nl, sp, search)
            for row in candidates:
                rows.append({"scan": "phase", "scenario": f"K=3, GI={gain:g} dB", **row})
            if best is not None:
                phase[i, j] = best["n_followers"]
            print(
                f"[Fig.D2 phase] G_I={gain:g} dB, N_L={nl}: "
                f"N_F^dagger={'none' if best is None else int(best['n_followers'])}",
                flush=True,
            )

    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.2), constrained_layout=True)
    for label, _, color, marker in scenarios:
        axes[0].plot(nls, curve_values[label], color=color, marker=marker, markerfacecolor="none", label=label)
    axes[0].set_xlabel("Number of Leader Satellites")
    axes[0].set_ylabel(r"Parsimonious Followers $N_F^\dagger$")
    axes[0].set_title(r"$\gamma=-5$ dB; validated 3% near-optimal design")
    axes[0].legend(frameon=True, fancybox=False, edgecolor="black", ncol=2)
    finish(axes[0])
    image = axes[1].imshow(
        phase,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=[min(nls) - 150, max(nls) + 150, min(gains) - 2.5, max(gains) + 2.5],
        vmin=0,
        vmax=max(search.follower_grid),
    )
    axes[1].set_xticks(nls)
    axes[1].set_yticks(gains)
    axes[1].set_xlabel("Number of Leader Satellites")
    axes[1].set_ylabel("Interference Coupling Gain (dB)")
    axes[1].set_title(r"$\gamma=-5$ dB, $K=3$, $p_{\rm act}=0.5$, exact correlated audit")
    for i, gain in enumerate(gains):
        for j, nl in enumerate(nls):
            if np.isnan(phase[i, j]):
                axes[1].text(nl, gain, r"$\times$", ha="center", va="center", color="red", fontsize=11)
    fig.colorbar(image, ax=axes[1], label=r"$N_F^\dagger$")
    finish(axes[1])
    save(fig, "figD2_optimal_follower_phase")
    save_csv("figD2_optimal_follower_phase", rows)


def fig_d3(mode: str) -> None:
    """Fixed per-satellite power versus fixed cluster total power."""
    nfs = [0, 2, 5, 10, 15, 20, 30]
    configurations = [
        ("Fixed per-satellite power", dict(power_model="per_satellite"), "blue", "o"),
        (
            "Fixed cluster total power (20 dBW)",
            dict(power_model="fixed_cluster_total", cluster_power_dbw=20.0, leader_power_fraction=0.5),
            "red",
            "s",
        ),
    ]
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 3500, 700)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True)
    for idx, (label, kwargs, color, marker) in enumerate(configurations):
        rate_values, coverage_values = [], []
        for nf in nfs:
            p = SystemParams(n_leaders=1000, n_followers=nf, gamma_th_db=10.0)
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=30300 + idx * 100 + nf,
                bandwidth_scaled_noise=True,
                **kwargs,
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            rate_values.append(summary["mean_rate_gbps"])
            coverage_values.append(summary["default_e2e_coverage"])
            rows.append({"configuration": label, "n_followers": nf, **summary})
        axes[0].plot(nfs, rate_values, color=color, marker=marker, markerfacecolor="none", label=label)
        axes[1].plot(nfs, coverage_values, color=color, marker=marker, markerfacecolor="none", label=label)
    axes[0].set_xlabel("Number of Follower Satellites")
    axes[0].set_ylabel("Average Cluster Rate (Gbps)")
    axes[1].set_xlabel("Number of Follower Satellites")
    axes[1].set_ylabel(r"End-to-End Coverage at $10$ dB")
    axes[1].set_ylim(0.0, 1.02)
    for ax in axes:
        ax.legend(frameon=True, fancybox=False, edgecolor="black")
        finish(ax)
    save(fig, "figD3_power_consistency")
    save_csv("figD3_power_consistency", rows)


def fig_d4(mode: str) -> None:
    """Altitude and follower-cap sensitivity."""
    altitudes = [400, 600, 800, 1000, 1200]
    caps = [0.2, 0.5, 1.0, 2.0, 3.0]
    rate = np.zeros((len(caps), len(altitudes)))
    coverage = np.zeros_like(rate)
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 3000, 600)
    for i, cap in enumerate(caps):
        for j, altitude in enumerate(altitudes):
            p = SystemParams(
                n_leaders=1000,
                n_followers=10,
                altitude_m=altitude * 1000.0,
                theta_cap_rad=math.radians(cap),
                gamma_th_db=10.0,
            )
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=40400 + i * 100 + j,
                bandwidth_scaled_noise=True,
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            rate[i, j] = summary["mean_rate_gbps"]
            coverage[i, j] = summary["default_e2e_coverage"]
            rows.append({"altitude_km": altitude, "theta_cap_deg": cap, **summary})
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True)
    im0 = axes[0].imshow(rate, origin="lower", aspect="auto", cmap="viridis")
    im1 = axes[1].imshow(coverage, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=1)
    for ax, title in zip(axes, ["Average cluster rate", r"End-to-end coverage at $10$ dB"]):
        ax.set_xticks(range(len(altitudes)), altitudes)
        ax.set_yticks(range(len(caps)), caps)
        ax.set_xlabel("Altitude (km)")
        ax.set_ylabel(r"Follower Cap Angle $\theta_{\rm cap}$ (deg)")
        ax.set_title(title)
        finish(ax)
    fig.colorbar(im0, ax=axes[0], label="Gbps")
    fig.colorbar(im1, ax=axes[1], label="Probability")
    save(fig, "figD4_geometry_sensitivity")
    save_csv("figD4_geometry_sensitivity", rows)


def fig_d5(mode: str) -> None:
    """Mean, median, and lower-tail rates under both power-consistency models."""
    nfs = [0, 2, 5, 10, 15, 20, 30]
    configs = [
        ("Per-satellite", dict(power_model="per_satellite")),
        ("Fixed cluster total", dict(power_model="fixed_cluster_total", cluster_power_dbw=20.0, leader_power_fraction=0.5)),
    ]
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 4000, 750)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True, sharey=True)
    for ax, (label, kwargs) in zip(axes, configs):
        means, medians, p05 = [], [], []
        for nf in nfs:
            p = SystemParams(n_leaders=1000, n_followers=nf)
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=50500 + nf,
                bandwidth_scaled_noise=True,
                **kwargs,
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            means.append(summary["mean_rate_gbps"])
            medians.append(summary["rate_median_gbps"])
            p05.append(summary["rate_p05_gbps"])
            rows.append({"configuration": label, "n_followers": nf, **summary})
        ax.plot(nfs, means, "-o", color="blue", markerfacecolor="none", label="Mean")
        ax.plot(nfs, medians, "-s", color="#00a83b", markerfacecolor="none", label="Median")
        ax.plot(nfs, p05, "-d", color="red", markerfacecolor="none", label="5th percentile")
        ax.set_title(label)
        ax.set_xlabel("Number of Follower Satellites")
        ax.legend(frameon=True, fancybox=False, edgecolor="black")
        finish(ax)
    axes[0].set_ylabel("Cluster Rate (Gbps)")
    save(fig, "figD5_percentile_rates")
    save_csv("figD5_percentile_rates", rows)


def fig_d6(mode: str) -> None:
    """Shared reuse-color correlation and its end-to-end reliability impact."""
    thresholds = np.arange(0.0, 21.0, 5.0)
    n = trials_for(mode, 4000, 800)
    p = SystemParams(n_leaders=500, n_followers=10)
    configurations = [
        ("Independent RB colors", False, "blue", "o"),
        ("Shared cluster reuse color", True, "red", "s"),
    ]
    rows: list[dict[str, object]] = []
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True)
    correlations = []
    for idx, (label, shared, color, marker) in enumerate(configurations):
        sp = scenario_params(
            "orthogonal_full_reuse",
            trials=n,
            seed=60600,
            interference_method="exact",
            reuse_factor=3,
            activity_probability=0.5,
            interference_gain_db=-10.0,
            shared_reuse_color=shared,
            bandwidth_scaled_noise=True,
        )
        samples = simulate_sinr_samples(p, sp)
        coverage = end_to_end_coverage_curve(samples, thresholds)
        correlation = float(np.corrcoef(samples["i_leader_rb"], samples["i_follower_rb"][:, 0])[0, 1])
        correlations.append(correlation)
        axes[0].plot(thresholds, coverage, color=color, marker=marker, markerfacecolor="none", label=label)
        for threshold, value in zip(thresholds, coverage):
            rows.append({"configuration": label, "threshold_db": threshold, "e2e_coverage": value, "rb_correlation": correlation})
    axes[0].set_xlabel("SINR Threshold (dB)")
    axes[0].set_ylabel("End-to-End Coverage Probability")
    axes[0].set_ylim(0.0, 1.02)
    axes[0].legend(frameon=True, fancybox=False, edgecolor="black")
    finish(axes[0])
    axes[1].bar([0, 1], correlations, color=["blue", "red"], width=0.62)
    axes[1].set_xticks([0, 1], ["Independent", "Shared color"])
    axes[1].set_ylabel("Leader/Follower RB INR Correlation")
    axes[1].set_ylim(0.0, max(correlations) * 1.25)
    finish(axes[1])
    save(fig, "figD6_shared_interference_correlation")
    save_csv("figD6_shared_interference_correlation", rows)


def fig_d7(mode: str) -> None:
    """Follower availability and ISL duplex-cost sensitivity."""
    probabilities = [0.4, 0.6, 0.8, 1.0]
    duplex = [0.5, 1.0]
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 5000, 800)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.05), constrained_layout=True)
    for idx, factor in enumerate(duplex):
        rates, coverages = [], []
        for probability in probabilities:
            p = SystemParams(n_leaders=1000, n_followers=10, gamma_th_db=10.0)
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=70700 + int(probability * 10),
                follower_availability_probability=probability,
                isl_duplex_factor=factor,
                bandwidth_scaled_noise=True,
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            rates.append(summary["mean_rate_gbps"])
            coverages.append(summary["default_e2e_coverage"])
            rows.append({"duplex_factor": factor, "follower_availability": probability, **summary})
        label = "Full-duplex / independent ISL" if factor == 1.0 else "Equal-slot half-duplex"
        color = "blue" if factor == 1.0 else "red"
        marker = "o" if factor == 1.0 else "s"
        axes[0].plot(probabilities, rates, color=color, marker=marker, markerfacecolor="none", label=label)
        axes[1].plot(probabilities, coverages, color=color, marker=marker, markerfacecolor="none", label=label)
    axes[0].set_xlabel("Follower Availability Probability")
    axes[0].set_ylabel("Average Cluster Rate (Gbps)")
    axes[1].set_xlabel("Follower Availability Probability")
    axes[1].set_ylabel(r"End-to-End Coverage at $10$ dB")
    axes[1].set_ylim(0.0, 1.02)
    for ax in axes:
        ax.legend(frameon=True, fancybox=False, edgecolor="black")
        finish(ax)
    save(fig, "figD7_availability_duplex")
    save_csv("figD7_availability_duplex", rows)


def fig_d8(mode: str) -> None:
    """Residual sensitivity: visibility angle, cluster power, and ISL threshold."""
    rows: list[dict[str, object]] = []
    n = trials_for(mode, 3500, 700)
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.15), constrained_layout=True)

    visible_angles = [20, 30, 45, 60, 75]
    visible_coverage: list[float] = []
    for angle in visible_angles:
        p = SystemParams(
            n_leaders=1000,
            n_followers=10,
            theta_max_rad=math.radians(angle),
            gamma_th_db=10.0,
        )
        sp = scenario_params(
            "coordinated",
            trials=n,
            seed=80800 + angle,
            bandwidth_scaled_noise=True,
        )
        summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
        visible_coverage.append(summary["default_e2e_coverage"])
        rows.append({"panel": "visibility_angle", "theta_max_deg": angle, **summary})
    axes[0].plot(visible_angles, visible_coverage, "-o", color="blue", markerfacecolor="none")
    axes[0].set_xlabel(r"Maximum Visible Angle $\theta_{\max}$ (deg)")
    axes[0].set_ylabel(r"End-to-End Coverage at $10$ dB")
    axes[0].set_ylim(0.0, 1.02)
    finish(axes[0])

    cluster_powers = [10, 15, 20, 25, 30]
    for nf, color, marker in [(0, "black", "o"), (5, "blue", "s"), (10, "red", "d")]:
        rates: list[float] = []
        for power in cluster_powers:
            p = SystemParams(n_leaders=1000, n_followers=nf)
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=81800 + 10 * nf + power,
                bandwidth_scaled_noise=True,
                power_model="fixed_cluster_total",
                cluster_power_dbw=float(power),
                leader_power_fraction=0.5,
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            rates.append(summary["mean_rate_gbps"])
            rows.append(
                {
                    "panel": "cluster_total_power",
                    "cluster_power_dbw": power,
                    "n_followers": nf,
                    **summary,
                }
            )
        axes[1].plot(
            cluster_powers,
            rates,
            color=color,
            marker=marker,
            markerfacecolor="none",
            label=rf"$N_F={nf}$",
        )
    axes[1].set_xlabel("Ground-Link Cluster Total Power (dBW)")
    axes[1].set_ylabel("Average Cluster Rate (Gbps)")
    axes[1].legend(frameon=True, fancybox=False, edgecolor="black")
    finish(axes[1])

    isl_thresholds = [-10, -5, 0, 5, 10]
    for nf, color, marker in [(2, "black", "o"), (5, "blue", "s"), (10, "red", "d")]:
        coverages: list[float] = []
        for threshold in isl_thresholds:
            p = SystemParams(n_leaders=1000, n_followers=nf, gamma_th_db=10.0)
            sp = scenario_params(
                "coordinated",
                trials=n,
                seed=82800 + 10 * nf,
                bandwidth_scaled_noise=True,
                gamma_lf_db=float(threshold),
            )
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            coverages.append(summary["default_e2e_coverage"])
            rows.append(
                {
                    "panel": "isl_threshold",
                    "gamma_lf_db": threshold,
                    "n_followers": nf,
                    **summary,
                }
            )
        axes[2].plot(
            isl_thresholds,
            coverages,
            color=color,
            marker=marker,
            markerfacecolor="none",
            label=rf"$N_F={nf}$",
        )
    axes[2].set_xlabel(r"ISL Threshold $\gamma_{\rm LF}$ (dB)")
    axes[2].set_ylabel(r"End-to-End Coverage at $10$ dB")
    axes[2].set_ylim(0.0, 1.02)
    axes[2].legend(frameon=True, fancybox=False, edgecolor="black")
    finish(axes[2])
    save(fig, "figD8_residual_sensitivity")
    save_csv("figD8_residual_sensitivity", rows)


FIGURES = {
    "figD1": fig_d1,
    "figD2": fig_d2,
    "figD3": fig_d3,
    "figD4": fig_d4,
    "figD5": fig_d5,
    "figD6": fig_d6,
    "figD7": fig_d7,
    "figD8": fig_d8,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--figure", choices=FIGURES)
    parser.add_argument("--mode", choices=["fast", "final"], default="final")
    args = parser.parse_args()
    setup_style()
    if args.all:
        for function in FIGURES.values():
            function(args.mode)
    elif args.figure:
        FIGURES[args.figure](args.mode)
    else:
        parser.error("use --all or --figure")


if __name__ == "__main__":
    main()
