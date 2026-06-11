"""Generate the comprehensive SINR-extension figures S1-S8."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.leo_follower_model import SystemParams, db_to_linear  # noqa: E402
from src.sinr_model import (  # noqa: E402
    access_coverage_curve,
    binomial_confidence_interval,
    end_to_end_coverage_curve,
    estimate_boundary_follower_interference_fraction,
    scenario_params,
    semi_analytical_leader_metrics,
    simulate_sinr_samples,
    summarize_sinr_samples,
)


FIG_DIR = ROOT / "figures" / "sinr"
DATA_DIR = ROOT / "figures" / "sinr_data"


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "font.size": 8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.6,
            "lines.linewidth": 1.25,
            "lines.markersize": 4.8,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )


def finish(ax: plt.Axes, minor: bool = False) -> None:
    ax.grid(True, which="major", color="#888888", alpha=0.28, linewidth=0.45)
    if minor:
        ax.grid(True, which="minor", color="#999999", alpha=0.20, linestyle=":", linewidth=0.35)
    ax.tick_params(direction="in", top=True, right=True, width=0.6)


def save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)


def save_csv(name: str, header: list[str], rows: list[list[object]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / f"{name}.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(str(x) for x in row) + "\n")


def trials_for(mode: str, final: int, fast: int) -> int:
    return final if mode == "final" else fast


def fig_s1(mode: str) -> None:
    thresholds = np.arange(-25.0, 1.0, 5.0)
    p = SystemParams(n_leaders=1000, n_followers=10)
    scenarios = [
        ("Noise-limited", scenario_params("noise_limited"), "0.35", "s", "--"),
        ("Full reuse + SIC", scenario_params("full_reuse_sic", interference_method="exact"), "red", "^", "-"),
        ("Orthogonal, reuse 1", scenario_params("orthogonal_full_reuse"), "blue", "o", "-"),
        ("Coordinated", scenario_params("coordinated"), "#00a83b", "d", "-"),
    ]
    rows: list[list[object]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    for idx, (label, base, color, marker, ls) in enumerate(scenarios):
        n = trials_for(mode, 3500, 900)
        if base.resource_model == "full_reuse_sic":
            n = trials_for(mode, 1000, 350)
        samples = simulate_sinr_samples(p, base.with_updates(trials=n, seed=1100 + idx))
        cov = access_coverage_curve(samples, thresholds)
        ax.plot(thresholds, cov, ls, color=color, marker=marker, markerfacecolor="none", label=label)
        for th, value in zip(thresholds, cov):
            succ = int(round(value * n))
            _, lo, hi = binomial_confidence_interval(succ, n)
            rows.append([label, th, value, lo, hi, n])
    ax.set_xlabel("SINR Threshold (dB)")
    ax.set_ylabel("Access Coverage Probability")
    ax.set_xlim(thresholds.min(), thresholds.max())
    ax.set_ylim(0.0, 1.02)
    finish(ax)
    ax.legend(loc="lower left", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS1_resource_model_coverage")
    save_csv("figS1_resource_model_coverage", ["scenario", "threshold_db", "coverage", "ci_low", "ci_high", "trials"], rows)


def fig_s2(mode: str) -> None:
    nfs = np.array([0, 2, 5, 10, 15, 20, 30])
    rows: list[list[object]] = []
    access_vals, e2e_vals, e2e_lo, e2e_hi = [], [], [], []
    n = trials_for(mode, 3500, 900)
    for nf in nfs:
        p = SystemParams(n_leaders=1000, n_followers=int(nf))
        samples = simulate_sinr_samples(p, scenario_params("coordinated", trials=n, seed=2200 + int(nf)))
        access = float(access_coverage_curve(samples, [p.gamma_th_db])[0])
        e2e = float(end_to_end_coverage_curve(samples, [p.gamma_th_db])[0])
        _, lo, hi = binomial_confidence_interval(int(round(e2e * n)), n)
        access_vals.append(access)
        e2e_vals.append(e2e)
        e2e_lo.append(lo)
        e2e_hi.append(hi)
        rows.append([int(nf), access, e2e, lo, hi])
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    ax.plot(nfs, access_vals, "--s", color="0.35", markerfacecolor="none", label="Access coverage")
    ax.errorbar(nfs, e2e_vals, yerr=[np.array(e2e_vals) - np.array(e2e_lo), np.array(e2e_hi) - np.array(e2e_vals)], color="blue", marker="o", capsize=2.5, label="End-to-end relay coverage")
    ax.set_xlabel("Number of Follower Satellites")
    ax.set_ylabel(r"Coverage Probability at $-5$ dB")
    ax.set_xlim(nfs.min(), nfs.max())
    ax.set_ylim(0.70, 1.01)
    finish(ax)
    ax.legend(loc="lower right", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS2_access_vs_e2e")
    save_csv("figS2_access_vs_e2e", ["n_followers", "access_coverage", "e2e_coverage", "e2e_ci_low", "e2e_ci_high"], rows)


def fig_s3(mode: str) -> None:
    nfs = np.array([0, 2, 5, 10, 15, 20, 30])
    scenarios = [
        ("Noise-limited", "noise_limited", "0.35", "s", "--"),
        ("Orthogonal, reuse 1", "orthogonal_full_reuse", "blue", "o", "-"),
        ("Coordinated", "coordinated", "#00a83b", "d", "-"),
    ]
    rows: list[list[object]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    n = trials_for(mode, 2800, 700)
    for idx, (label, name, color, marker, ls) in enumerate(scenarios):
        vals, los, his = [], [], []
        for nf in nfs:
            samples = simulate_sinr_samples(SystemParams(n_leaders=1000, n_followers=int(nf)), scenario_params(name, trials=n, seed=3300 + 100 * idx + int(nf)))
            summary = summarize_sinr_samples(samples)
            vals.append(summary["mean_rate_gbps"])
            los.append(summary["rate_ci_low_gbps"])
            his.append(summary["rate_ci_high_gbps"])
            rows.append([label, int(nf), summary["mean_rate_gbps"], summary["rate_ci_low_gbps"], summary["rate_ci_high_gbps"], summary["default_e2e_coverage"]])
        ax.errorbar(nfs, vals, yerr=[np.array(vals) - np.array(los), np.array(his) - np.array(vals)], color=color, marker=marker, markerfacecolor="none", linestyle=ls, capsize=2, label=label)
    ax.set_xlabel("Number of Follower Satellites")
    ax.set_ylabel("Average Cluster Rate (Gbps)")
    ax.set_xlim(nfs.min(), nfs.max())
    ax.set_yscale("log")
    finish(ax, minor=True)
    ax.legend(loc="upper left", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS3_rate_resource_models")
    save_csv("figS3_rate_resource_models", ["scenario", "n_followers", "rate_gbps", "ci_low_gbps", "ci_high_gbps", "e2e_coverage"], rows)


def fig_s4(mode: str) -> None:
    nls = np.array([300, 600, 900, 1200, 1500, 1800])
    scenarios = [
        ("Orthogonal, reuse 1", "orthogonal_full_reuse", "blue", "o"),
        ("Coordinated", "coordinated", "#00a83b", "d"),
    ]
    rows: list[list[object]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    n = trials_for(mode, 2200, 650)
    base = SystemParams()
    earth_area_km2 = 4.0 * np.pi * (base.earth_radius_m / 1000.0) ** 2
    for idx, (label, name, color, marker) in enumerate(scenarios):
        net, net_lo, net_hi = [], [], []
        for nl in nls:
            samples = simulate_sinr_samples(SystemParams(n_leaders=int(nl), n_followers=10), scenario_params(name, trials=n, seed=4400 + 100 * idx + int(nl)))
            summary = summarize_sinr_samples(samples)
            throughput = summary["mean_rate_gbps"] * nl / 1000.0
            throughput_lo = summary["rate_ci_low_gbps"] * nl / 1000.0
            throughput_hi = summary["rate_ci_high_gbps"] * nl / 1000.0
            spherical_efficiency = throughput * 1e12 / (base.bandwidth_lu_hz * earth_area_km2)
            _, cov_lo, cov_hi = binomial_confidence_interval(int(round(summary["default_e2e_coverage"] * n)), n)
            net.append(throughput)
            net_lo.append(throughput_lo)
            net_hi.append(throughput_hi)
            rows.append([
                label,
                int(nl),
                summary["mean_rate_gbps"],
                summary["rate_ci_low_gbps"],
                summary["rate_ci_high_gbps"],
                throughput,
                throughput_lo,
                throughput_hi,
                spherical_efficiency,
                summary["default_e2e_coverage"],
                cov_lo,
                cov_hi,
            ])
        ax.errorbar(
            nls,
            net,
            yerr=[np.array(net) - np.array(net_lo), np.array(net_hi) - np.array(net)],
            color=color,
            marker=marker,
            markerfacecolor="none",
            capsize=2,
            label=label,
        )
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Network Throughput Proxy (Tbps)")
    finish(ax)
    ax.legend(loc="best", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS4_network_throughput")
    save_csv(
        "figS4_network_throughput",
        [
            "scenario",
            "n_leaders",
            "cluster_rate_gbps",
            "cluster_rate_ci_low_gbps",
            "cluster_rate_ci_high_gbps",
            "network_throughput_proxy_tbps",
            "network_throughput_proxy_ci_low_tbps",
            "network_throughput_proxy_ci_high_tbps",
            "spherical_spectral_efficiency_proxy_bps_hz_km2",
            "e2e_coverage",
            "e2e_coverage_ci_low",
            "e2e_coverage_ci_high",
        ],
        rows,
    )


def fig_s5(mode: str) -> None:
    reuse = np.array([1, 2, 3, 4, 6])
    gains = np.array([-30, -20, -10, 0])
    activity = np.array([0.1, 0.25, 0.5, 0.75, 1.0])
    rate = np.zeros((gains.size, reuse.size))
    coverage = np.zeros_like(rate)
    rows: list[list[object]] = []
    n = trials_for(mode, 5000, 800)
    p = SystemParams(n_leaders=1000, n_followers=10)
    for i, gain in enumerate(gains):
        for j, r in enumerate(reuse):
            sp = scenario_params("orthogonal_full_reuse", trials=n, seed=5500 + i * 50 + j, reuse_factor=int(r), activity_probability=0.5, interference_gain_db=float(gain))
            summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
            rate[i, j] = summary["mean_rate_gbps"]
            coverage[i, j] = summary["default_e2e_coverage"]
            _, cov_lo, cov_hi = binomial_confidence_interval(int(round(coverage[i, j] * n)), n)
            rows.append([
                "reuse_gain",
                int(r),
                0.5,
                int(gain),
                rate[i, j],
                summary["rate_ci_low_gbps"],
                summary["rate_ci_high_gbps"],
                coverage[i, j],
                cov_lo,
                cov_hi,
            ])
    activity_rate, activity_coverage = [], []
    for idx, probability in enumerate(activity):
        sp = scenario_params(
            "orthogonal_full_reuse",
            trials=n,
            seed=5750 + idx,
            reuse_factor=3,
            activity_probability=float(probability),
            interference_gain_db=-10.0,
        )
        summary = summarize_sinr_samples(simulate_sinr_samples(p, sp))
        activity_rate.append(summary["mean_rate_gbps"])
        activity_coverage.append(summary["default_e2e_coverage"])
        _, cov_lo, cov_hi = binomial_confidence_interval(int(round(summary["default_e2e_coverage"] * n)), n)
        rows.append([
            "activity",
            3,
            probability,
            -10,
            summary["mean_rate_gbps"],
            summary["rate_ci_low_gbps"],
            summary["rate_ci_high_gbps"],
            summary["default_e2e_coverage"],
            cov_lo,
            cov_hi,
        ])
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 2.9), constrained_layout=True)
    im0 = axes[0].imshow(rate, origin="lower", aspect="auto", cmap="viridis", extent=[reuse.min() - 0.5, reuse.max() + 0.5, gains.min() - 5, gains.max() + 5])
    im1 = axes[1].imshow(coverage, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=1, extent=[reuse.min() - 0.5, reuse.max() + 0.5, gains.min() - 5, gains.max() + 5])
    for ax, title in zip(axes, ["Cluster rate", "End-to-end coverage"]):
        ax.set_xlabel("Frequency Reuse Factor")
        ax.set_ylabel("Interference Coupling Gain (dB)")
        ax.set_title(title)
        ax.set_xticks(reuse)
        ax.set_yticks(gains)
        finish(ax)
    fig.colorbar(im0, ax=axes[0], label="Gbps")
    fig.colorbar(im1, ax=axes[1], label="Probability")
    axes[2].plot(activity, activity_rate, "-o", color="blue", markerfacecolor="none", label="Rate")
    axes[2].set_xlabel("Cochannel Activity Probability")
    axes[2].set_ylabel("Cluster Rate (Gbps)", color="blue")
    axes[2].tick_params(axis="y", labelcolor="blue")
    axes[2].set_title(r"Activity scan ($K=3$, $G_I=-10$ dB)")
    activity_axis = axes[2].twinx()
    activity_axis.plot(activity, activity_coverage, "-s", color="red", markerfacecolor="none", label="Coverage")
    activity_axis.set_ylabel("End-to-End Coverage", color="red")
    activity_axis.tick_params(axis="y", labelcolor="red")
    activity_axis.set_ylim(0.0, 1.0)
    finish(axes[2])
    save(fig, "figS5_coordination_sensitivity")
    save_csv(
        "figS5_coordination_sensitivity",
        [
            "scan_type",
            "reuse_factor",
            "activity_probability",
            "interference_gain_db",
            "rate_gbps",
            "rate_ci_low_gbps",
            "rate_ci_high_gbps",
            "e2e_coverage",
            "e2e_coverage_ci_low",
            "e2e_coverage_ci_high",
        ],
        rows,
    )


def fig_s6(mode: str) -> None:
    thresholds = np.arange(-25.0, 1.0, 5.0)
    p = SystemParams(n_leaders=900, n_followers=0)
    sp = scenario_params("orthogonal_full_reuse")
    semi, _ = semi_analytical_leader_metrics(p, sp, thresholds)
    n = trials_for(mode, 7000, 1600)
    exact = simulate_sinr_samples(p, sp.with_updates(trials=n, seed=6600, interference_method="exact"))
    mc = np.array([np.mean(exact["sinr_lu"] >= db_to_linear(t)) for t in thresholds])
    intervals = [binomial_confidence_interval(int(round(value * n)), n) for value in mc]
    mc_lo = np.array([item[1] for item in intervals])
    mc_hi = np.array([item[2] for item in intervals])
    rows = [[th, s, m, lo, hi, abs(s - m)] for th, s, m, lo, hi in zip(thresholds, semi, mc, mc_lo, mc_hi)]
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    ax.plot(thresholds, semi, "-s", color="red", markerfacecolor="none", label="Semi-analytical moment match")
    ax.errorbar(
        thresholds,
        mc,
        yerr=[mc - mc_lo, mc_hi - mc],
        fmt="o",
        color="blue",
        markerfacecolor="none",
        capsize=2,
        label="Exact-geometry Monte Carlo",
    )
    ax.set_xlabel("SINR Threshold (dB)")
    ax.set_ylabel("Leader-Branch Coverage")
    ax.set_ylim(0, 1.02)
    finish(ax)
    ax.legend(loc="lower left", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS6_semi_analytical_validation")
    save_csv(
        "figS6_semi_analytical_validation",
        ["threshold_db", "semi_analytical", "exact_mc", "exact_mc_ci_low", "exact_mc_ci_high", "absolute_error"],
        rows,
    )


def fig_s7(mode: str) -> None:
    nls = np.array([300, 600, 900, 1200, 1500, 1800])
    n = trials_for(mode, 300_000, 70_000)
    values = [estimate_boundary_follower_interference_fraction(SystemParams(n_leaders=int(nl)), samples=n, seed=7700) for nl in nls]
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    ax.plot(nls, 100.0 * np.array(values), "-o", color="purple", markerfacecolor="none")
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Boundary Follower Interference Share (%)")
    ax.set_ylim(bottom=0)
    finish(ax)
    save(fig, "figS7_boundary_correction")
    save_csv("figS7_boundary_correction", ["n_leaders", "boundary_interference_fraction"], [[int(nl), v] for nl, v in zip(nls, values)])


def fig_s8(mode: str) -> None:
    nfs = np.array([0, 2, 5, 10, 15, 20, 30])
    configurations = [
        ("Reuse 1, 0 dB", dict(reuse_factor=1, activity_probability=1.0, interference_gain_db=0.0), "red"),
        ("Reuse 3, -10 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-10.0), "blue"),
        ("Reuse 3, -20 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-20.0), "#00a83b"),
    ]
    rows: list[list[object]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.15))
    n = trials_for(mode, 2500, 700)
    for idx, (label, params, color) in enumerate(configurations):
        rates, covs = [], []
        for nf in nfs:
            sp = scenario_params("orthogonal_full_reuse", trials=n, seed=8800 + idx * 100 + int(nf), **params)
            summary = summarize_sinr_samples(simulate_sinr_samples(SystemParams(n_leaders=1000, n_followers=int(nf)), sp))
            rates.append(summary["mean_rate_gbps"])
            covs.append(summary["default_e2e_coverage"])
            _, cov_lo, cov_hi = binomial_confidence_interval(int(round(summary["default_e2e_coverage"] * n)), n)
            rows.append([
                label,
                int(nf),
                summary["mean_rate_gbps"],
                summary["rate_ci_low_gbps"],
                summary["rate_ci_high_gbps"],
                summary["default_e2e_coverage"],
                cov_lo,
                cov_hi,
            ])
        ax.plot(covs, rates, "-o", color=color, markerfacecolor="none", label=label)
        endpoint_offsets = {
            0: {0: (5, 7), 30: (5, -18)},
            1: {0: (-34, 8), 30: (-52, -12)},
            2: {0: (5, -14), 30: (8, 9)},
        }
        for x, y, nf in zip(covs, rates, nfs):
            if nf in [0, 30]:
                ax.annotate(rf"$N_F={nf}$", (x, y), xytext=endpoint_offsets[idx][int(nf)], textcoords="offset points", fontsize=7)
    ax.set_xlabel(r"End-to-End Coverage at $-5$ dB")
    ax.set_ylabel("Average Cluster Rate (Gbps)")
    finish(ax)
    ax.legend(loc="best", frameon=True, fancybox=False, edgecolor="black")
    save(fig, "figS8_rate_reliability_frontier")
    save_csv(
        "figS8_rate_reliability_frontier",
        [
            "configuration",
            "n_followers",
            "rate_gbps",
            "rate_ci_low_gbps",
            "rate_ci_high_gbps",
            "e2e_coverage",
            "e2e_coverage_ci_low",
            "e2e_coverage_ci_high",
        ],
        rows,
    )


FIGURES = {
    "figS1": fig_s1,
    "figS2": fig_s2,
    "figS3": fig_s3,
    "figS4": fig_s4,
    "figS5": fig_s5,
    "figS6": fig_s6,
    "figS7": fig_s7,
    "figS8": fig_s8,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--fig", choices=sorted(FIGURES), action="append")
    parser.add_argument("--mode", choices=["fast", "final"], default="fast")
    args = parser.parse_args()
    setup_style()
    selected = list(FIGURES) if args.all or not args.fig else args.fig
    for name in selected:
        print(f"Generating {name}...")
        FIGURES[name](args.mode)
    print(f"SINR figures written to {FIG_DIR}")


if __name__ == "__main__":
    main()
