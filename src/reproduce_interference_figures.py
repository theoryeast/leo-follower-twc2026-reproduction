"""Generate interference-extension figures I1-I5."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.interference_model import (  # noqa: E402
    InterferenceParams,
    average_rate_cluster_middle_with_interference,
    coverage_curve,
    mean_interference_coefficients,
    mean_interference_inr,
    simulate_network_samples,
    summarize_samples,
)
from src.leo_follower_model import SystemParams, as_gbps, average_rate_cluster_middle  # noqa: E402


FIG_DIR = ROOT / "figures" / "interference"
DATA_DIR = ROOT / "figures" / "interference_data"


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "font.size": 8,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.6,
            "lines.linewidth": 1.3,
            "lines.markersize": 5.2,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )


def finish_axis(ax: plt.Axes, minor: bool = False) -> None:
    ax.grid(True, which="major", color="#7f7f7f", alpha=0.28, linewidth=0.45)
    if minor:
        ax.grid(True, which="minor", color="#8f8f8f", alpha=0.22, linestyle=":", linewidth=0.35)
    ax.tick_params(direction="in", top=True, right=True, width=0.6)


def save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)


def save_csv(name: str, header: list[str], rows: list[list[float | int | str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / f"{name}.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(str(x) for x in row) + "\n")


def fig_i1() -> None:
    n_leaders = np.array([300, 600, 900, 1200, 1500, 1800])
    n_followers = [0, 5, 10, 20, 30]
    rows: list[list[float | int | str]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.1))
    colors = {0: "black", 5: "red", 10: "#00aa00", 20: "blue", 30: "purple"}
    for nf in n_followers:
        vals = []
        for nl in n_leaders:
            p = SystemParams(n_leaders=int(nl), n_followers=nf)
            leader_coeff, follower_coeff = mean_interference_coefficients(p)
            total = leader_coeff + nf * follower_coeff
            vals.append(total)
            rows.append([int(nl), nf, leader_coeff, nf * follower_coeff, total, 10 * np.log10(max(total, 1e-15))])
        ax.plot(n_leaders, 10 * np.log10(np.maximum(vals, 1e-15)), marker="o", color=colors[nf], label=rf"$N_F={nf}$")
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Mean INR (dB)")
    ax.set_xlim(n_leaders.min(), n_leaders.max())
    finish_axis(ax)
    ax.legend(frameon=True, fancybox=False, edgecolor="black", framealpha=1, loc="lower right")
    save(fig, "figI1_mean_inr")
    save_csv("figI1_mean_inr", ["n_leaders", "n_followers", "leader_inr", "follower_inr", "total_inr", "total_inr_db"], rows)


def fig_i2(mode: str) -> None:
    thresholds = np.arange(-30, 1, 5, dtype=float)
    n_followers = [0, 5, 10, 20, 30]
    rows: list[list[float | int | str]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.1))
    colors = {0: "black", 5: "red", 10: "#00aa00", 20: "blue", 30: "purple"}
    trials = 900 if mode == "fast" else 1800
    for nf in n_followers:
        p = SystemParams(n_leaders=1500, n_followers=nf)
        samples = simulate_network_samples(p, InterferenceParams(trials=trials, seed=2100 + nf, follower_samples_per_cluster=2))
        cov = coverage_curve(samples, thresholds)
        ax.plot(thresholds, cov, marker="o", color=colors[nf], label=rf"$N_F={nf}$")
        for th, cv in zip(thresholds, cov):
            rows.append(["same_frequency", nf, th, cv])
    baseline = simulate_network_samples(
        SystemParams(n_leaders=1500, n_followers=10),
        InterferenceParams(trials=trials, seed=2199, follower_samples_per_cluster=2, interference_enabled=False),
    )
    baseline_cov = coverage_curve(baseline, thresholds)
    ax.plot(thresholds, baseline_cov, "--", color="0.35", marker="s", markerfacecolor="none", label=r"No ICI, $N_F=10$")
    for th, cv in zip(thresholds, baseline_cov):
        rows.append(["noise_limited", 10, th, cv])
    ax.set_xlabel("SINR Threshold (dB)")
    ax.set_ylabel("Coverage Probability")
    ax.set_xlim(thresholds.min(), thresholds.max())
    ax.set_ylim(0, 1.02)
    finish_axis(ax)
    ax.legend(frameon=True, fancybox=False, edgecolor="black", framealpha=1, loc="lower right")
    save(fig, "figI2_sinr_coverage")
    save_csv("figI2_sinr_coverage", ["scenario", "n_followers", "threshold_db", "coverage"], rows)


def fig_i3(mode: str) -> None:
    n_followers = np.array([0, 2, 5, 10, 15, 20, 25, 30])
    rows: list[list[float | int | str]] = []
    trials = 1000 if mode == "fast" else 2000
    rate_i = []
    lo = []
    hi = []
    rate_no_i = []
    for nf in n_followers:
        p = SystemParams(n_leaders=1500, n_followers=int(nf))
        samples = simulate_network_samples(p, InterferenceParams(trials=trials, seed=3100 + int(nf), follower_samples_per_cluster=2))
        summary = summarize_samples(samples)
        no_interference = average_rate_cluster_middle(p) / 1e9
        rate_i.append(summary["mean_rate_gbps"])
        lo.append(summary["mean_rate_ci_low_gbps"])
        hi.append(summary["mean_rate_ci_high_gbps"])
        rate_no_i.append(no_interference)
        rows.append([int(nf), no_interference, summary["mean_rate_gbps"], summary["mean_rate_ci_low_gbps"], summary["mean_rate_ci_high_gbps"], summary["mean_inr"]])
    fig, ax = plt.subplots(figsize=(4.5, 3.1))
    ax.plot(n_followers, rate_no_i, "--", color="0.35", marker="s", markerfacecolor="none", label="Noise-limited baseline")
    ax.errorbar(n_followers, rate_i, yerr=[np.array(rate_i) - np.array(lo), np.array(hi) - np.array(rate_i)], color="blue", marker="o", capsize=3, label="Same-frequency interference")
    ax.set_xlabel("Number of Follower Satellites")
    ax.set_ylabel("Average Cluster Rate (Gbps)")
    ax.set_xlim(n_followers.min(), n_followers.max())
    finish_axis(ax)
    ax.legend(frameon=True, fancybox=False, edgecolor="black", framealpha=1)
    save(fig, "figI3_cluster_rate")
    save_csv("figI3_cluster_rate", ["n_followers", "noise_limited_rate_gbps", "interference_rate_gbps", "ci_low_gbps", "ci_high_gbps", "mean_inr"], rows)


def fig_i4(mode: str) -> None:
    n_leaders = np.array([300, 600, 900, 1200, 1500, 1800])
    n_followers = [0, 10, 20]
    rows: list[list[float | int | str]] = []
    fig, ax = plt.subplots(figsize=(4.5, 3.1))
    colors = {0: "black", 10: "#00aa00", 20: "blue"}
    for nf in n_followers:
        throughputs = []
        for nl in n_leaders:
            p = SystemParams(n_leaders=int(nl), n_followers=nf)
            inr = mean_interference_inr(p)
            rate = average_rate_cluster_middle_with_interference(p, inr) / 1e9
            net_tbps = rate * nl / 1000.0
            throughputs.append(net_tbps)
            rows.append([int(nl), nf, inr, rate, net_tbps])
        ax.plot(n_leaders, throughputs, color=colors[nf], marker="o", label=rf"$N_F={nf}$")
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Network Throughput (Tbps)")
    finish_axis(ax)
    ax.legend(frameon=True, fancybox=False, edgecolor="black", framealpha=1)
    save(fig, "figI4_network_throughput")
    save_csv("figI4_network_throughput", ["n_leaders", "n_followers", "mean_inr", "rate_gbps", "network_throughput_tbps"], rows)


def fig_i5() -> None:
    n_leaders = np.array([300, 600, 900, 1200, 1500, 1800])
    n_followers = np.array([0, 5, 10, 15, 20, 25, 30])
    grid = np.zeros((n_followers.size, n_leaders.size))
    rows: list[list[float | int | str]] = []
    for j, nl in enumerate(n_leaders):
        for i, nf in enumerate(n_followers):
            p = SystemParams(n_leaders=int(nl), n_followers=int(nf))
            inr = mean_interference_inr(p)
            rate = average_rate_cluster_middle_with_interference(p, inr) / 1e9
            grid[i, j] = rate
            rows.append([int(nl), int(nf), inr, rate])
    fig, ax = plt.subplots(figsize=(4.7, 3.3))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis", extent=[n_leaders.min(), n_leaders.max(), n_followers.min(), n_followers.max()])
    best_idx = np.argmax(grid, axis=0)
    ax.plot(n_leaders, n_followers[best_idx], color="white", marker="o", linewidth=1.2, label="Best in grid")
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Number of Followers")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Mean-field Rate (Gbps)")
    ax.legend(frameon=True, fancybox=False, edgecolor="black", framealpha=0.9, loc="upper right")
    finish_axis(ax)
    save(fig, "figI5_nf_nl_heatmap")
    save_csv("figI5_nf_nl_heatmap", ["n_leaders", "n_followers", "mean_inr", "mean_field_rate_gbps"], rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--mode", choices=["fast", "final"], default="fast")
    args = parser.parse_args()
    setup_style()
    fig_i1()
    fig_i2(args.mode)
    fig_i3(args.mode)
    fig_i4(args.mode)
    fig_i5()
    print(f"Interference figures written to {FIG_DIR}")


if __name__ == "__main__":
    main()
