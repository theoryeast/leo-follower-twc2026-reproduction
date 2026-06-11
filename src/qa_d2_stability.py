"""Repeated-seed stability audit for the Fig.D2 parsimonious deployment map."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deployment_optimization_model import DeploymentSearch, optimize_follower_count  # noqa: E402
from src.sinr_model import scenario_params  # noqa: E402


SCENARIOS = [
    ("K=1, -20 dB", dict(reuse_factor=1, activity_probability=0.5, interference_gain_db=-20.0)),
    ("K=3, -10 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-10.0)),
    ("K=3, -20 dB", dict(reuse_factor=3, activity_probability=0.5, interference_gain_db=-20.0)),
    ("K=6, -20 dB", dict(reuse_factor=6, activity_probability=0.5, interference_gain_db=-20.0)),
    ("K=3, p_act=0.1", dict(reuse_factor=3, activity_probability=0.1, interference_gain_db=-20.0)),
]
N_LEADERS = [600, 900, 1200, 1500, 1800]


def run_stability_audit(repeats: int, mode: str) -> dict[str, object]:
    scan_trials = 1800 if mode == "final" else 500
    validation_trials = 3500 if mode == "final" else 900
    search = DeploymentSearch(
        coverage_target=0.99,
        conservative_constraint=True,
        independent_validation=True,
        validation_trials=validation_trials,
        rate_tolerance_relative=0.03,
        reselect_on_validation=True,
        exact_audit=False,
    )

    d2_path = ROOT / "figures" / "deployment_data" / "figD2_optimal_follower_phase.csv"
    d2 = pd.read_csv(d2_path)
    selected = d2[
        (d2["scan"] == "curve")
        & d2["selected"].astype(str).str.lower().isin(["true", "1"])
    ]
    final_reference = {
        (str(row["scenario"]), int(row["n_leaders"])): int(row["n_followers"])
        for _, row in selected.iterrows()
    }
    final_audit_rank = {
        (str(row["scenario"]), int(row["n_leaders"])): int(row["exact_audit_rank"])
        for _, row in selected.iterrows()
    }
    validation_near = d2[
        (d2["scan"] == "curve")
        & d2["validation_feasible"].astype(str).str.lower().isin(["true", "1"])
        & d2["validation_within_rate_tolerance"].astype(str).str.lower().isin(["true", "1"])
    ].copy()
    validation_near = validation_near.sort_values(
        ["scenario", "n_leaders", "n_followers", "validation_mean_rate_gbps"],
        ascending=[True, True, True, False],
    ).drop_duplicates(["scenario", "n_leaders"])
    validation_reference = {
        (str(row["scenario"]), int(row["n_leaders"])): int(row["n_followers"])
        for _, row in validation_near.iterrows()
    }

    rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for scenario_index, (label, kwargs) in enumerate(SCENARIOS):
        for n_leaders in N_LEADERS:
            values: list[int] = []
            for repeat in range(repeats):
                sp = scenario_params(
                    "orthogonal_full_reuse",
                    trials=scan_trials,
                    seed=810_000 + 10_000 * scenario_index + 100 * n_leaders + repeat,
                    bandwidth_scaled_noise=True,
                    power_model="fixed_cluster_total",
                    cluster_power_dbw=20.0,
                    leader_power_fraction=0.5,
                    **kwargs,
                )
                best, _ = optimize_follower_count(n_leaders, sp, search)
                selected_nf = -1 if best is None else int(best["n_followers"])
                values.append(selected_nf)
                rows.append(
                    {
                        "scenario": label,
                        "n_leaders": n_leaders,
                        "repeat": repeat,
                        "selected_n_followers": selected_nf,
                        "selected_alpha": float("nan") if best is None else float(best["alpha"]),
                        "validation_e2e_coverage_ci_low": (
                            float("nan")
                            if best is None
                            else float(best["validation_e2e_coverage_ci_low"])
                        ),
                        "validation_mean_rate_gbps": (
                            float("nan")
                            if best is None
                            else float(best["validation_mean_rate_gbps"])
                        ),
                    }
                )
            valid = [value for value in values if value >= 0]
            counts = {value: valid.count(value) for value in sorted(set(valid))}
            mode_nf = max(counts, key=lambda value: (counts[value], -value)) if counts else -1
            validation_ref = validation_reference.get((label, n_leaders), -1)
            final_ref = final_reference.get((label, n_leaders), -1)
            audit_rank = final_audit_rank.get((label, n_leaders), -1)
            final_within_range = bool(valid and min(valid) <= final_ref <= max(valid))
            summaries.append(
                {
                    "scenario": label,
                    "n_leaders": n_leaders,
                    "validation_selected_n_followers": validation_ref,
                    "final_exact_audited_n_followers": final_ref,
                    "final_exact_audit_rank": audit_rank,
                    "repeat_min_n_followers": min(valid) if valid else -1,
                    "repeat_max_n_followers": max(valid) if valid else -1,
                    "repeat_mode_n_followers": mode_nf,
                    "mode_support": 0.0 if not valid else counts[mode_nf] / len(valid),
                    "validation_reference_within_repeat_range": bool(
                        valid and min(valid) <= validation_ref <= max(valid)
                    ),
                    "final_within_repeat_range": final_within_range,
                    "final_supported_or_moved_by_exact_audit": bool(
                        final_within_range or audit_rank > 1
                    ),
                    "all_repeats_feasible": len(valid) == repeats,
                    "selection_counts": ";".join(
                        f"{value}:{counts[value]}" for value in sorted(counts)
                    ),
                }
            )

    data_path = ROOT / "figures" / "deployment_data" / "figD2_selection_stability.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary_frame = pd.DataFrame(summaries)
    all_repeats_feasible = bool(summary_frame["all_repeats_feasible"].all())
    all_final_supported = bool(
        summary_frame["final_supported_or_moved_by_exact_audit"].all()
    )
    report_path = ROOT / "qa" / "d2_selection_stability_report.md"
    lines = [
        "# Fig.D2 多随机种子选择稳定性审查",
        "",
        "该审查重复执行独立样本速率重选，但不重复高成本完整几何审计。"
        "它用于量化离散候选和有限样本导致的选择波动；最终 Fig.D2 点仍以完整几何共享颜色审计为准。",
        "",
        f"- 重复次数：`{repeats}`",
        f"- 每次扫描样本：`{scan_trials}`",
        f"- 每次独立复验样本：`{validation_trials}`",
        f"- 所有重复均存在可行点：`{all_repeats_feasible}`",
        f"- 最终点均位于重复范围内或由完整相关审计拒绝更小候选后上调：`{all_final_supported}`",
        "",
        "| 场景 | $N_L$ | 独立复验点 | 最终完整审计点 | 审计序号 | 重复范围 | 众数 | 众数支持率 | 计数 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['scenario']} | {row['n_leaders']} | "
            f"{row['validation_selected_n_followers']} | "
            f"{row['final_exact_audited_n_followers']} | "
            f"{row['final_exact_audit_rank']} | "
            f"{row['repeat_min_n_followers']}--{row['repeat_max_n_followers']} | "
            f"{row['repeat_mode_n_followers']} | {row['mode_support']:.0%} | "
            f"{row['selection_counts']} |"
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "若重复范围包含多个离散值，应把它解释为近最优部署区间，而不是唯一精确最优数量。"
            "最终点通过更严格的完整几何相关干扰覆盖审计，因此可能位于边缘矩近似的重复范围之外；"
            "这种移动表示相关干扰门禁改变了可行性，而不是自动判为选择不稳定。",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "all_repeats_feasible": all_repeats_feasible,
        "all_final_supported_or_moved_by_exact_audit": all_final_supported,
        "maximum_selection_range_width": int(
            (summary_frame["repeat_max_n_followers"] - summary_frame["repeat_min_n_followers"]).max()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--mode", choices=["fast", "final"], default="final")
    args = parser.parse_args()
    result = run_stability_audit(max(args.repeats, 1), args.mode)
    print(result)
    if (
        not result["all_repeats_feasible"]
        or not result["all_final_supported_or_moved_by_exact_audit"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
