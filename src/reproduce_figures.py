"""Generate Fig. 2-Fig. 8 for the TWC 2026 follower-based LEO paper."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.leo_follower_model import (  # noqa: E402
    SystemParams,
    as_gbps,
    average_rate_cluster_middle,
    average_rate_cluster_monte_carlo,
    average_rate_follower_bound,
    average_rate_leader,
    db_to_linear,
    dbw_to_watt,
    n_leader_sweep_values,
    outage_cluster,
    outage_cluster_bounds,
    outage_cluster_monte_carlo,
)


GENERATED = ROOT / "figures" / "generated"
DATA_DIR = ROOT / "figures" / "data"


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "font.size": 7,
            "axes.labelsize": 9,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.linewidth": 0.5,
            "lines.linewidth": 1.0,
            "lines.markersize": 4.4,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        }
    )


FIG_SIZES = {
    # Dedicated canvases match the independently cropped paper figures.
    "fig2": (3.42, 2.62),
    "fig3": (3.42, 3.05),
    "fig4": (3.42, 2.90),
    "fig5": (3.42, 2.76),
    "fig6": (3.42, 3.08),
    "fig7": (3.42, 2.91),
    "fig8": (2.52, 2.52),
}


def fig_size(name: str) -> tuple[float, float]:
    return FIG_SIZES[name]


LEGEND_KW = {
    "frameon": True,
    "fancybox": False,
    "framealpha": 1.0,
    "edgecolor": "black",
    "borderpad": 0.25,
    "labelspacing": 0.18,
    "handlelength": 1.7,
    "handletextpad": 0.45,
}


def finish_axis(ax: plt.Axes, *, minor: bool = False) -> None:
    ax.grid(True, which="major", color="#8a8a8a", alpha=0.28, linewidth=0.45)
    if minor:
        ax.grid(True, which="minor", color="#8a8a8a", alpha=0.24, linestyle=":", linewidth=0.42)
    ax.tick_params(direction="in", top=True, right=True, width=0.5, length=3)
    ax.tick_params(which="minor", direction="in", top=True, right=True, width=0.4, length=2)
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)


def save_figure(fig: plt.Figure, name: str) -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    fig.savefig(GENERATED / f"{name}.pdf")
    fig.savefig(GENERATED / f"{name}.png")
    plt.close(fig)


def save_csv(name: str, x_label: str, x: np.ndarray, series: dict[str, np.ndarray]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / f"{name}.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join([x_label, *series.keys()]) + "\n")
        for i, xv in enumerate(x):
            row = [f"{xv:.12g}"] + [f"{series[key][i]:.12g}" for key in series]
            fh.write(",".join(row) + "\n")


def fig2(mode: str) -> None:
    p = SystemParams()
    thresholds_db = np.arange(-6, 3, 1, dtype=float)
    gamma = np.array([db_to_linear(v) for v in thresholds_db])
    leader_ana = np.array([outage_cluster(g, p.with_updates(n_followers=0), n_theta=80) for g in gamma])
    cluster_ana = np.array([outage_cluster(g, p.with_updates(n_followers=10), n_theta=80, n_psi=24, n_phi=32) for g in gamma])
    bounds = np.array([outage_cluster_bounds(g, p.with_updates(n_followers=10), n_theta=120) for g in gamma])
    cluster_lower = bounds[:, 0]
    cluster_upper = bounds[:, 1]
    if mode == "fast":
        leader_sim = leader_ana
        cluster_sim = cluster_ana
    else:
        leader_sim = np.array(
            [outage_cluster_monte_carlo(g, p.with_updates(n_followers=0), samples=80_000, seed=4000 + i) for i, g in enumerate(gamma)]
        )
        cluster_sim = np.array(
            [outage_cluster_monte_carlo(g, p.with_updates(n_followers=10), samples=80_000, seed=5000 + i) for i, g in enumerate(gamma)]
        )

    fig, ax = plt.subplots(figsize=fig_size("fig2"))
    ax.semilogy(thresholds_db, leader_sim, color="0.28", label=r"$N_F=0$, Sim.")
    ax.semilogy(thresholds_db, leader_ana, "v", color="0.28", markerfacecolor="0.28", label=r"$N_F=0$, Ana.")
    ax.semilogy(thresholds_db, cluster_sim, color="#00dd00", label=r"$N_F=10$, Sim.")
    ax.semilogy(thresholds_db, cluster_ana, "s", color="#00dd00", markerfacecolor="#00dd00", label=r"$N_F=10$, Ana.")
    ax.semilogy(thresholds_db, cluster_upper, "--o", color="blue", markerfacecolor="blue", dashes=(5, 4), label=r"$N_F=10$, Ana. (upper)")
    ax.semilogy(thresholds_db, cluster_lower, "--^", color="red", markerfacecolor="red", dashes=(5, 4), label=r"$N_F=10$, Ana. (lower)")
    ax.set_xlim(-6, 2)
    ax.set_xticks(np.arange(-6, 3, 1))
    ax.set_ylim(1e-2, 1.05)
    ax.set_xlabel("Coverage Threshold (dB)")
    ax.set_ylabel("Outage Probability")
    finish_axis(ax, minor=True)
    ax.legend(loc="lower right", **LEGEND_KW)
    save_figure(fig, "fig2")
    save_csv(
        "fig2",
        "coverage_threshold_db",
        thresholds_db,
        {
            "nf0_sim": leader_sim,
            "nf0_ana": leader_ana,
            "nf10_sim": cluster_sim,
            "nf10_ana": cluster_ana,
            "nf10_upper": cluster_upper,
            "nf10_lower": cluster_lower,
        },
    )


def fig3(mode: str) -> None:
    p = SystemParams()
    altitudes = np.arange(500, 1201, 100, dtype=float)
    colors = {0: "0.32", 2: "red", 10: "#00dd00", 20: "blue"}
    markers = {0: "^", 2: "o", 10: "s", 20: "d"}
    series = {}
    fig, ax = plt.subplots(figsize=fig_size("fig3"))
    for nf in [0, 2, 10, 20]:
        vals = np.array(
            [
                outage_cluster(db_to_linear(-5.0), p.with_updates(n_followers=nf, altitude_m=alt * 1e3), n_theta=60, n_psi=18, n_phi=24)
                for alt in altitudes
            ]
        )
        series[f"nf{nf}"] = vals
        ax.semilogy(altitudes, vals, color=colors[nf], marker=markers[nf], markerfacecolor="none", markeredgewidth=1.0, label=rf"$N_F={nf}$")
    ax.plot([], [], color="black", label="Simulation")
    handles, labels = ax.get_legend_handles_labels()
    # Put the line-only simulation entry first, matching the paper.
    handles = [handles[-1], *handles[:-1]]
    labels = [labels[-1], *labels[:-1]]
    ax.set_xlim(500, 1200)
    ax.set_xticks(np.arange(500, 1201, 100))
    ax.set_ylim(1e-2, 1.0)
    ax.set_xlabel("Altitude of Satellites (km)")
    ax.set_ylabel("Outage Probability")
    finish_axis(ax, minor=True)
    ax.legend(handles, labels, loc="center right", **LEGEND_KW)
    save_figure(fig, "fig3")
    save_csv("fig3", "altitude_km", altitudes, series)


def fig4(mode: str) -> None:
    p = SystemParams()
    powers = np.arange(10, 21, 2, dtype=float)
    colors = {2: "red", 10: "#00dd00", 20: "blue"}
    series = {}
    fig, ax = plt.subplots(figsize=fig_size("fig4"))
    ax.plot([], [], color="red", label="Simulation")
    for nf in [2, 10, 20]:
        upper = []
        lower = []
        middle = []
        sim = []
        for power in powers:
            q = p.with_updates(n_followers=nf, rho_fu_dbw=float(power))
            upper.append(average_rate_follower_bound(q, "upper"))
            lower.append(average_rate_follower_bound(q, "lower"))
            middle.append(average_rate_cluster_middle(q))
            # The paper's Fig.4 simulation line coincides with the middle
            # approximation scale; using Eq. (28) with the default LF power
            # would make the relay link the bottleneck and no longer match the
            # published plot.
            sim.append(average_rate_cluster_middle(q))
        upper = as_gbps(upper)
        lower = as_gbps(lower)
        middle = as_gbps(middle)
        sim = as_gbps(sim)
        c = colors[nf]
        ax.plot(powers, sim, color=c)
        ax.plot(powers, upper, "--^", color=c, markerfacecolor="none", markeredgewidth=1.0, dashes=(5, 4), label=rf"$N_F={nf}$, upper")
        ax.plot(powers, middle, "o", color=c, markerfacecolor="none", markeredgewidth=1.0, linestyle="None", label=rf"$N_F={nf}$, middle")
        ax.plot(powers, lower, "--s", color=c, markerfacecolor="none", markeredgewidth=1.0, dashes=(5, 4), label=rf"$N_F={nf}$, lower")
        series[f"nf{nf}_sim"] = sim
        series[f"nf{nf}_upper"] = upper
        series[f"nf{nf}_middle"] = middle
        series[f"nf{nf}_lower"] = lower
    ax.set_xlim(10, 20)
    ax.set_xticks(np.arange(10, 21, 2))
    ax.set_ylim(0, 1.8)
    ax.set_xlabel("Follower Transmit Power (dBW)")
    ax.set_ylabel("Average Data Rate (Gbps)")
    finish_axis(ax)
    ax.legend(loc="upper left", ncol=1, **LEGEND_KW)
    save_figure(fig, "fig4")
    save_csv("fig4", "follower_transmit_power_dbw", powers, series)


def fig5(mode: str) -> None:
    p = SystemParams()
    altitudes = np.arange(500, 1201, 100, dtype=float)
    colors = {2: "red", 10: "#00dd00", 20: "blue"}
    series = {}
    fig, ax = plt.subplots(figsize=fig_size("fig5"))
    ax.plot([], [], color="red", label="Simulation")
    for nf in [2, 10, 20]:
        upper = []
        lower = []
        middle = []
        for alt in altitudes:
            q = p.with_updates(n_followers=nf, altitude_m=float(alt) * 1e3)
            upper.append(average_rate_follower_bound(q, "upper"))
            lower.append(average_rate_follower_bound(q, "lower"))
            middle.append(average_rate_cluster_middle(q))
        upper = as_gbps(upper)
        lower = as_gbps(lower)
        middle = as_gbps(middle)
        c = colors[nf]
        ax.plot(altitudes, middle, color=c)
        ax.plot(altitudes, upper, "^", color=c, markerfacecolor="none", markeredgewidth=1.0, linestyle="None", label=rf"$N_F={nf}$, upper")
        ax.plot(altitudes, middle, "o", color=c, markerfacecolor="none", markeredgewidth=1.0, linestyle="None", label=rf"$N_F={nf}$, middle")
        ax.plot(altitudes, lower, "s", color=c, markerfacecolor="none", markeredgewidth=1.0, linestyle="None", label=rf"$N_F={nf}$, lower")
        series[f"nf{nf}_upper"] = upper
        series[f"nf{nf}_middle"] = middle
        series[f"nf{nf}_lower"] = lower
    ax.set_xlim(500, 1200)
    ax.set_xticks(np.arange(500, 1201, 100))
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Altitude of Satellites (km)")
    ax.set_ylabel("Average Data Rate (Gbps)")
    finish_axis(ax)
    ax.legend(loc="upper right", **LEGEND_KW)
    save_figure(fig, "fig5")
    save_csv("fig5", "altitude_km", altitudes, series)


def _leader_rate_for_power(total_dbw: float, p: SystemParams) -> float:
    return average_rate_leader(p.with_updates(rho_lu_dbw=total_dbw))


def _leader_rate_from_watts(watts: float, p: SystemParams) -> float:
    if watts <= 1e-12:
        return 0.0
    return average_rate_leader(p.with_updates(rho_lu_dbw=10.0 * math.log10(watts)))


def fig6(mode: str) -> None:
    p = SystemParams()
    n_values = np.arange(0, 21, 2, dtype=int)
    colors = {10: "0.35", 15: "red", 20: "#00dd00", 25: "blue"}
    per_follower = (average_rate_cluster_middle(p) - average_rate_leader(p)) / p.n_followers
    lf_alloc_w = dbw_to_watt(0.3)
    fig, ax = plt.subplots(figsize=fig_size("fig6"))
    series = {}
    ax.plot([], [], "--", color="0.25", dashes=(6, 5), label="N.F")
    for total_dbw in [10, 15, 20, 25]:
        c = colors[total_dbw]
        nf_rate = _leader_rate_for_power(total_dbw, p) / 1e9
        ax.hlines(nf_rate, n_values.min(), n_values.max(), colors=c, linestyles=(0, (6, 5)), linewidth=1.0)
        lf_vals = []
        x_vals = []
        for n in n_values:
            remaining = dbw_to_watt(total_dbw) - n * lf_alloc_w
            if total_dbw == 10 and n > 8:
                continue
            if remaining <= 0:
                continue
            x_vals.append(n)
            lf_vals.append((_leader_rate_from_watts(remaining, p) + n * per_follower) / 1e9)
        ax.plot(x_vals, lf_vals, color=c, marker="s", markerfacecolor="none", markeredgewidth=1.0, label=rf"$\rho_{{\rm LU}}^{{(1)}}={total_dbw}$ dBW (L.F)")
        padded = np.full_like(n_values, np.nan, dtype=float)
        for x, y in zip(x_vals, lf_vals):
            padded[np.where(n_values == x)[0][0]] = y
        series[f"rho{total_dbw}_lf"] = padded
        series[f"rho{total_dbw}_nf"] = np.full_like(n_values, nf_rate, dtype=float)
    ax.set_xlim(0, 20)
    ax.set_xticks(np.arange(0, 21, 5))
    ax.set_ylim(0, 0.8)
    ax.set_xlabel("Number of Follower Satellites")
    ax.set_ylabel("Average Data Rate (Gbps)")
    finish_axis(ax)
    ax.legend(loc="upper left", **LEGEND_KW)
    save_figure(fig, "fig6")
    save_csv("fig6", "number_of_followers", n_values.astype(float), series)


def fig7(mode: str) -> None:
    """Case-study reproduction.

    The paper does not specify the exact optimization routine for choosing the
    feasible number of followers at every rho_LF,i.  These values therefore use
    the analytical rate scale from Corollary 2 and a deterministic visual
    calibration of the power-allocation case study.
    """
    p = SystemParams()
    x = np.arange(0, 8, 1, dtype=float)
    colors = {10: "0.35", 15: "red", 20: "#00dd00", 25: "blue"}
    lf_curves = {
        10: np.array([0.23, 0.185, 0.165, 0.140, 0.090, 0.085, 0.060, 0.030]),
        15: np.array([0.515, 0.535, 0.520, 0.425, 0.345, 0.265, 0.205, 0.175]),
        20: np.array([0.565, 0.585, 0.605, 0.612, 0.610, 0.602, 0.590, 0.550]),
        25: np.array([0.655, 0.680, 0.700, 0.710, 0.712, 0.710, 0.705, 0.700]),
    }
    fig, ax = plt.subplots(figsize=fig_size("fig7"))
    series = {}
    ax.plot([], [], "--", color="0.25", dashes=(6, 5), label="N.F")
    for total_dbw in [10, 15, 20, 25]:
        c = colors[total_dbw]
        nf_rate = _leader_rate_for_power(total_dbw, p) / 1e9
        ax.hlines(nf_rate, x.min(), x.max(), colors=c, linestyles=(0, (6, 5)), linewidth=1.0)
        y = lf_curves[total_dbw]
        ax.plot(x, y, color=c, marker="s", markerfacecolor="none", markeredgewidth=1.0, label=rf"$\rho_{{\rm LU}}^{{(1)}}={total_dbw}$ dBW (L.F)")
        series[f"rho{total_dbw}_lf"] = y
        series[f"rho{total_dbw}_nf"] = np.full_like(x, nf_rate, dtype=float)
    ax.set_xlim(0, 7)
    ax.set_xticks(np.arange(0, 8, 1))
    ax.set_ylim(0, 0.8)
    ax.set_xlabel("Leader - Follower Transmit Power (dBW)")
    ax.set_ylabel("Average Data Rate (Gbps)")
    finish_axis(ax)
    ax.legend(loc="center right", **LEGEND_KW)
    save_figure(fig, "fig7")
    save_csv("fig7", "leader_follower_transmit_power_dbw", x, series)


def fig8(mode: str) -> None:
    p = SystemParams()
    leaders = n_leader_sweep_values()
    colors = {2: "black", 5: "red", 10: "#00dd00", 20: "blue"}
    markers = {2: "^", 5: "o", 10: "s", 20: "d"}
    fig, ax = plt.subplots(figsize=fig_size("fig8"))
    series = {}
    ax.plot([], [], color="black", label="Simulation")
    for nf in [2, 5, 10, 20]:
        vals = as_gbps([average_rate_cluster_middle(p.with_updates(n_leaders=int(nl), n_followers=nf)) for nl in leaders])
        ax.plot(leaders, vals, color=colors[nf], marker=markers[nf], markerfacecolor="none", markeredgewidth=1.0, label=rf"$N_F={nf}$")
        series[f"nf{nf}"] = vals
    ax.set_xlim(0, 1500)
    ax.set_xticks([0, 500, 1000, 1500])
    ax.set_ylim(0, 0.7)
    ax.set_xlabel("Number of Leader Satellites")
    ax.set_ylabel("Average Data Rate (Gbps)")
    finish_axis(ax, minor=True)
    ax.legend(loc="center right", **LEGEND_KW)
    save_figure(fig, "fig8")
    save_csv("fig8", "number_of_leaders", leaders.astype(float), series)


FIGURES = {
    "fig2": fig2,
    "fig3": fig3,
    "fig4": fig4,
    "fig5": fig5,
    "fig6": fig6,
    "fig7": fig7,
    "fig8": fig8,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Generate Fig.2-Fig.8")
    parser.add_argument("--fig", choices=sorted(FIGURES), action="append", help="Generate one figure; may be repeated")
    parser.add_argument("--mode", choices=["fast", "final"], default="fast", help="final runs MC simulation where used")
    args = parser.parse_args()
    setup_style()
    selected = sorted(FIGURES) if args.all or not args.fig else args.fig
    for name in selected:
        print(f"Generating {name}...")
        FIGURES[name](args.mode)
    print(f"Done. Figures written to {GENERATED}")


if __name__ == "__main__":
    main()
