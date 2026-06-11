"""Generate the auditable QA report for deployment figures D1-D8."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deployment_optimization_model import run_deployment_validation  # noqa: E402


FIGURE_NAMES = [
    "figD1_allocation_strategies",
    "figD2_optimal_follower_phase",
    "figD3_power_consistency",
    "figD4_geometry_sensitivity",
    "figD5_percentile_rates",
    "figD6_shared_interference_correlation",
    "figD7_availability_duplex",
    "figD8_residual_sensitivity",
]


def dataframe_is_finite(path: Path) -> bool:
    frame = pd.read_csv(path)
    if frame.empty:
        return False
    numeric = frame.select_dtypes(include=[np.number])
    values = numeric.to_numpy(dtype=float)
    observed = values[~np.isnan(values)]
    return bool(observed.size > 0 and np.all(np.isfinite(observed)))


def main() -> None:
    figure_dir = ROOT / "figures" / "deployment"
    data_dir = ROOT / "figures" / "deployment_data"
    validation = run_deployment_validation()

    figures = [figure_dir / f"{name}.png" for name in FIGURE_NAMES]
    figure_pdfs = [figure_dir / f"{name}.pdf" for name in FIGURE_NAMES]
    data_paths = [data_dir / f"{name}.csv" for name in FIGURE_NAMES]
    frames = {path.stem: pd.read_csv(path) for path in data_paths}

    d1 = frames["figD1_allocation_strategies"]
    d2 = frames["figD2_optimal_follower_phase"]
    d3 = frames["figD3_power_consistency"]
    d4 = frames["figD4_geometry_sensitivity"]
    d5 = frames["figD5_percentile_rates"]
    d6 = frames["figD6_shared_interference_correlation"]
    d7 = frames["figD7_availability_duplex"]
    d8 = frames["figD8_residual_sensitivity"]
    stability_path = data_dir / "figD2_selection_stability.csv"
    stability = pd.read_csv(stability_path) if stability_path.exists() else pd.DataFrame()

    d1_pivot = d1.pivot(index="n_followers", columns="strategy", values="mean_rate_gbps")
    optimized_column = next(column for column in d1_pivot.columns if "Rate-optimal" in column)
    d1_competitors = [column for column in d1_pivot.columns if column != optimized_column]

    selected = d2[d2["selected"].astype(str).str.lower().isin(["true", "1"])]
    group_count = d2.groupby(["scan", "scenario", "n_leaders"]).ngroups
    selected_curve = selected[selected["scan"] == "curve"].copy()
    if not stability.empty:
        stability_ranges = (
            stability.groupby(["scenario", "n_leaders"])["selected_n_followers"]
            .agg(["min", "max"])
            .reset_index()
        )
        stability_joined = selected_curve.merge(
            stability_ranges,
            on=["scenario", "n_leaders"],
            how="left",
        )
    else:
        stability_joined = pd.DataFrame()

    d3_per = d3[d3["configuration"] == "Fixed per-satellite power"].set_index("n_followers")
    d3_fixed = d3[d3["configuration"].str.startswith("Fixed cluster total")].set_index("n_followers")

    d6_corr = d6.groupby("configuration")["rb_correlation"].first()
    d6_cov10 = d6[d6["threshold_db"] == 10.0].set_index("configuration")["e2e_coverage"]

    d7_rate = d7.pivot(index="follower_availability", columns="duplex_factor", values="mean_rate_gbps")
    d7_cov = d7.pivot(index="follower_availability", columns="duplex_factor", values="default_e2e_coverage")

    detailed_tex = (ROOT / "theory" / "resource_consistent_sinr_full_derivation_v1.tex").read_text(encoding="utf-8")
    results_tex = (ROOT / "theory" / "deployment_results_analysis.tex").read_text(encoding="utf-8")
    checks = {
        "deployment_validation_gate": bool(validation["all_acceptance_checks_pass"]),
        "all_eight_png_figures_exist": all(path.exists() and path.stat().st_size > 0 for path in figures),
        "all_eight_pdf_figures_exist": all(path.exists() and path.stat().st_size > 0 for path in figure_pdfs),
        "all_eight_csv_files_exist": all(path.exists() and path.stat().st_size > 0 for path in data_paths),
        "all_csv_numeric_values_finite": all(dataframe_is_finite(path) for path in data_paths),
        "d1_rate_optimum_dominates_grid_comparators": bool(
            all(np.all(d1_pivot[optimized_column] >= d1_pivot[column] - 1e-12) for column in d1_competitors)
        ),
        "d1_alpha_is_not_a_single_boundary_value": bool(
            d1[d1["strategy"] == optimized_column]["alpha"].nunique() > 2
        ),
        "d2_exactly_one_selected_design_per_group": bool(len(selected) == group_count),
        "d2_threshold_is_explicitly_minus5_db": bool(
            len(selected) == group_count and np.allclose(selected["gamma_th_db"], -5.0)
        ),
        "d2_all_alpha_candidates_receive_independent_validation": bool(
            d2["validation_mean_rate_gbps"].notna().all()
            and d2["validation_e2e_coverage_ci_low"].notna().all()
        ),
        "d2_scan_records_complete_candidate_metrics": bool(
            d2["e2e_coverage_ci_low"].notna().all()
            and d2["mean_rate_gbps"].notna().all()
        ),
        "d2_independent_validation_uses_wilson_lower_bound_at_099": bool(
            len(selected) == group_count
            and np.all(selected["validation_e2e_coverage_ci_low"] >= 0.99)
            and np.all(selected["validation_feasible"].astype(str).str.lower().isin(["true", "1"]))
        ),
        "d2_independent_validation_rechecks_near_optimal_rate": bool(
            len(selected) == group_count
            and np.all(selected["validation_within_rate_tolerance"].astype(str).str.lower().isin(["true", "1"]))
            and np.all(
                selected["validation_mean_rate_gbps"]
                >= 0.97 * selected["validation_maximum_feasible_rate_gbps"] - 1e-12
            )
        ),
        "d2_exact_correlated_audit_uses_wilson_lower_bound_at_099": bool(
            len(selected) == group_count
            and np.all(selected["exact_audit_e2e_coverage_ci_low"] >= 0.99)
            and np.all(selected["exact_audit_feasible"].astype(str).str.lower().isin(["true", "1"]))
            and np.all(selected["exact_audit_shared_reuse_color"].astype(str).str.lower().isin(["true", "1"]))
        ),
        "d2_exact_correlated_rate_agrees_with_validation_within_5_percent": bool(
            len(selected) == group_count
            and np.all(
                np.abs(
                    selected["exact_audit_mean_rate_gbps"]
                    / selected["validation_mean_rate_gbps"]
                    - 1.0
                )
                <= 0.05
            )
        ),
        "d2_repeated_seed_stability_artifacts_exist": bool(
            stability_path.exists()
            and stability_path.stat().st_size > 0
            and (ROOT / "qa" / "d2_selection_stability_report.md").exists()
        ),
        "d2_final_points_are_seed_supported_or_moved_by_exact_audit": bool(
            not stability_joined.empty
            and stability_joined[["min", "max"]].notna().all().all()
            and np.all(
                (
                    (stability_joined["n_followers"] >= stability_joined["min"])
                    & (stability_joined["n_followers"] <= stability_joined["max"])
                )
                | (stability_joined["exact_audit_rank"] > 1)
            )
        ),
        "d2_uses_fixed_cluster_total_power": bool(
            len(selected) == group_count and np.all(selected["power_model"] == "fixed_cluster_total")
        ),
        "d2_selected_designs_are_within_validation_rate_tolerance": bool(
            len(selected) == group_count
            and np.all(
                selected["validation_mean_rate_gbps"]
                >= 0.97 * selected["validation_maximum_feasible_rate_gbps"] - 1e-12
            )
        ),
        "d3_power_accounting_changes_rate_conclusion": bool(
            d3_per.loc[30, "mean_rate_gbps"] > d3_per.loc[0, "mean_rate_gbps"]
            and d3_fixed.loc[30, "mean_rate_gbps"] < d3_fixed.loc[0, "mean_rate_gbps"]
        ),
        "d4_geometry_sensitivity_is_nontrivial": bool(
            d4["mean_rate_gbps"].max() > 2.0 * d4["mean_rate_gbps"].min()
            and d4["default_e2e_coverage"].max() > 2.0 * d4["default_e2e_coverage"].min()
        ),
        "d5_lower_tail_is_below_median": bool(np.all(d5["rate_p05_gbps"] <= d5["rate_median_gbps"])),
        "d6_shared_color_increases_correlation": bool(
            d6_corr["Shared cluster reuse color"] > d6_corr["Independent RB colors"]
        ),
        "d6_shared_color_changes_high_threshold_coverage": bool(
            abs(d6_cov10["Shared cluster reuse color"] - d6_cov10["Independent RB colors"]) > 1e-3
        ),
        "d7_full_duplex_rate_not_below_half_duplex": bool(np.all(d7_rate[1.0] >= d7_rate[0.5])),
        "d7_duplex_factor_does_not_change_sinr_coverage": bool(
            np.allclose(d7_cov[1.0], d7_cov[0.5], atol=0.0, rtol=0.0)
        ),
        "d8_covers_visibility_power_and_isl_threshold_sensitivity": bool(
            set(d8["panel"]) == {"visibility_angle", "cluster_total_power", "isl_threshold"}
        ),
        "d8_visibility_angle_sensitivity_is_nontrivial": bool(
            d8[d8["panel"] == "visibility_angle"]["default_e2e_coverage"].max()
            - d8[d8["panel"] == "visibility_angle"]["default_e2e_coverage"].min()
            > 0.01
        ),
        "d8_cluster_power_increases_rate_for_each_follower_count": bool(
            all(
                group.sort_values("cluster_power_dbw")["mean_rate_gbps"].iloc[-1]
                > group.sort_values("cluster_power_dbw")["mean_rate_gbps"].iloc[0]
                for _, group in d8[d8["panel"] == "cluster_total_power"].groupby("n_followers")
            )
        ),
        "d8_stricter_isl_threshold_does_not_improve_e2e_coverage": bool(
            all(
                np.all(np.diff(group.sort_values("gamma_lf_db")["default_e2e_coverage"]) <= 1e-12)
                for _, group in d8[d8["panel"] == "isl_threshold"].groupby("n_followers")
            )
        ),
        "detailed_tex_contains_bandwidth_noise_consistency": "带宽切分下的热噪声一致性" in detailed_tex,
        "detailed_tex_contains_parsimonious_deployment_definition": "统计稳健的简约 follower 数量" in detailed_tex,
        "detailed_tex_contains_related_work_and_bibliography": bool(
            "\\section{相关工作与本文定位}" in detailed_tex
            and "\\begin{thebibliography}{99}" in detailed_tex
            and detailed_tex.count("\\cite{") >= 5
        ),
        "results_tex_contains_d8_analysis": bool(
            "figD8_residual_sensitivity.pdf" in results_tex
            and "由 D1--D8 可得到以下部署规则" in results_tex
            and "最大可见角、集群总功率与 ISL 门限敏感性" in results_tex
        ),
        "results_tex_limits_d2_to_finite_candidate_grid": bool(
            "有限候选网格上的统计决策" in results_tex
            and "连续设计空间中的无条件全局最优解" in results_tex
        ),
        "required_chinese_tex_and_pdfs_exist": all(
            path.exists() and path.stat().st_size > 0
            for path in [
                ROOT / "theory" / "resource_consistent_sinr_full_derivation_v1.tex",
                ROOT / "theory" / "resource_consistent_sinr_full_derivation_v1.pdf",
                ROOT / "theory" / "deployment_results_analysis.tex",
                ROOT / "theory" / "deployment_results_analysis.pdf",
            ]
        ),
    }
    checks["all_checks_pass"] = all(checks.values())

    selected_curve = selected[selected["scan"] == "curve"].sort_values(["scenario", "n_leaders"])
    report = ROOT / "qa" / "deployment_review_report.md"
    lines = [
        "# 部署优化与资源一致性研究审查报告",
        "",
        "本报告由 `src/qa_deployment.py` 根据当前代码、CSV、图和 TeX 自动生成。",
        "",
        "## 自动验收",
        "",
        "| 检查项 | 结果 |",
        "|---|---:|",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## D2 最终简约部署点",
            "",
            "所有点均要求扫描样本和独立复验样本的 Wilson 95% 覆盖下界不低于 0.99，"
            "在独立复验样本中重新计算可行最大速率并选择 3% 以内的最小 follower 数量，"
            "随后再通过完整几何和共享复用颜色的相关干扰审计。",
            "",
            "| 场景 | $N_L$ | $N_F^\\dagger$ | $\\alpha$ | 独立复验覆盖下界 | 完整相关审计覆盖下界 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for _, row in selected_curve.iterrows():
        lines.append(
            f"| {row['scenario']} | {int(row['n_leaders'])} | {int(row['n_followers'])} | "
            f"{row['alpha']:.2f} | {row['validation_e2e_coverage_ci_low']:.4f} | "
            f"{row['exact_audit_e2e_coverage_ci_low']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## 关键数值闭环",
            "",
            f"- D3：固定单星功率下，$N_F=0\\to30$ 的平均速率由 "
            f"`{d3_per.loc[0, 'mean_rate_gbps']:.4f}` 增至 `{d3_per.loc[30, 'mean_rate_gbps']:.4f}` Gbps；"
            f"固定集群总功率下则由 `{d3_fixed.loc[0, 'mean_rate_gbps']:.4f}` 降至 "
            f"`{d3_fixed.loc[30, 'mean_rate_gbps']:.4f}` Gbps。",
            f"- D6：独立 RB 颜色相关系数为 `{d6_corr['Independent RB colors']:.4f}`，"
            f"公共复用颜色相关系数为 `{d6_corr['Shared cluster reuse color']:.4f}`。",
            f"- D7：半双工与全双工使用相同 SINR 覆盖事件，覆盖曲线逐点完全相同；"
            f"全双工平均速率始终不低于半双工。",
            "- D8：补充最大可见角、固定集群总功率和 ISL 门限敏感性，关闭目标清单中的剩余参数扫描缺口。",
            "",
            "## 解释边界",
            "",
            "- 通过表示当前模型内部数学、数值和交付物闭环，不等于真实星座外部验证。",
            "- 部署图采用固定链路总发射功率下的带宽缩放热噪声；旧 Fig.S1-S8 保留固定参考噪声口径以维持版本兼容。",
            "- D2 报告的是统计稳健的简约数量 $N_F^\\dagger$，不是宣称存在脱离容差与业务目标的唯一精确最优数量。",
            "- D2 的覆盖门限为 $-5$ dB；独立复验重新计算近最优速率集合，最终点再接受完整几何共享颜色相关干扰审计。",
            "- 多随机种子审查单独报告边缘矩独立复验的离散选择范围；最终完整审计点还可能因相关干扰门禁而移动。",
            "",
            f"## 结论：{'PASS' if checks['all_checks_pass'] else 'FAIL'}",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"checks": checks, "validation": validation}, indent=2, ensure_ascii=False))
    if not checks["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
