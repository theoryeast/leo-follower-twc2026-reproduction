# 部署优化与资源一致性研究审查报告

本报告由 `src/qa_deployment.py` 根据当前代码、CSV、图和 TeX 自动生成。

## 自动验收

| 检查项 | 结果 |
|---|---:|
| `deployment_validation_gate` | PASS |
| `all_eight_png_figures_exist` | PASS |
| `all_eight_pdf_figures_exist` | PASS |
| `all_eight_csv_files_exist` | PASS |
| `all_csv_numeric_values_finite` | PASS |
| `d1_rate_optimum_dominates_grid_comparators` | PASS |
| `d1_alpha_is_not_a_single_boundary_value` | PASS |
| `d2_exactly_one_selected_design_per_group` | PASS |
| `d2_threshold_is_explicitly_minus5_db` | PASS |
| `d2_all_alpha_candidates_receive_independent_validation` | PASS |
| `d2_scan_records_complete_candidate_metrics` | PASS |
| `d2_independent_validation_uses_wilson_lower_bound_at_099` | PASS |
| `d2_independent_validation_rechecks_near_optimal_rate` | PASS |
| `d2_exact_correlated_audit_uses_wilson_lower_bound_at_099` | PASS |
| `d2_exact_correlated_rate_agrees_with_validation_within_5_percent` | PASS |
| `d2_repeated_seed_stability_artifacts_exist` | PASS |
| `d2_final_points_are_seed_supported_or_moved_by_exact_audit` | PASS |
| `d2_uses_fixed_cluster_total_power` | PASS |
| `d2_selected_designs_are_within_validation_rate_tolerance` | PASS |
| `d3_power_accounting_changes_rate_conclusion` | PASS |
| `d4_geometry_sensitivity_is_nontrivial` | PASS |
| `d5_lower_tail_is_below_median` | PASS |
| `d6_shared_color_increases_correlation` | PASS |
| `d6_shared_color_changes_high_threshold_coverage` | PASS |
| `d7_full_duplex_rate_not_below_half_duplex` | PASS |
| `d7_duplex_factor_does_not_change_sinr_coverage` | PASS |
| `d8_covers_visibility_power_and_isl_threshold_sensitivity` | PASS |
| `d8_visibility_angle_sensitivity_is_nontrivial` | PASS |
| `d8_cluster_power_increases_rate_for_each_follower_count` | PASS |
| `d8_stricter_isl_threshold_does_not_improve_e2e_coverage` | PASS |
| `detailed_tex_contains_bandwidth_noise_consistency` | PASS |
| `detailed_tex_contains_parsimonious_deployment_definition` | PASS |
| `detailed_tex_contains_related_work_and_bibliography` | PASS |
| `results_tex_contains_d8_analysis` | PASS |
| `results_tex_limits_d2_to_finite_candidate_grid` | PASS |
| `required_chinese_tex_and_pdfs_exist` | PASS |
| `all_checks_pass` | PASS |

## D2 最终简约部署点

所有点均要求扫描样本和独立复验样本的 Wilson 95% 覆盖下界不低于 0.99，在独立复验样本中重新计算可行最大速率并选择 3% 以内的最小 follower 数量，随后再通过完整几何和共享复用颜色的相关干扰审计。

| 场景 | $N_L$ | $N_F^\dagger$ | $\alpha$ | 独立复验覆盖下界 | 完整相关审计覆盖下界 |
|---|---:|---:|---:|---:|---:|
| K=1, -20 dB | 600 | 30 | 0.65 | 0.9946 | 0.9934 |
| K=1, -20 dB | 900 | 20 | 0.65 | 0.9951 | 0.9909 |
| K=1, -20 dB | 1200 | 20 | 0.65 | 0.9941 | 0.9939 |
| K=1, -20 dB | 1500 | 20 | 0.50 | 0.9951 | 0.9926 |
| K=1, -20 dB | 1800 | 15 | 0.50 | 0.9922 | 0.9918 |
| K=3, -10 dB | 600 | 10 | 0.50 | 0.9933 | 0.9914 |
| K=3, -10 dB | 900 | 10 | 0.50 | 0.9961 | 0.9934 |
| K=3, -10 dB | 1200 | 10 | 0.50 | 0.9941 | 0.9934 |
| K=3, -10 dB | 1500 | 10 | 0.50 | 0.9946 | 0.9943 |
| K=3, -10 dB | 1800 | 10 | 0.50 | 0.9948 | 0.9939 |
| K=3, -20 dB | 600 | 10 | 0.50 | 0.9946 | 0.9943 |
| K=3, -20 dB | 900 | 5 | 0.35 | 0.9926 | 0.9947 |
| K=3, -20 dB | 1200 | 5 | 0.50 | 0.9933 | 0.9901 |
| K=3, -20 dB | 1500 | 5 | 0.50 | 0.9922 | 0.9918 |
| K=3, -20 dB | 1800 | 5 | 0.50 | 0.9943 | 0.9922 |
| K=3, p_act=0.1 | 600 | 5 | 0.35 | 0.9900 | 0.9905 |
| K=3, p_act=0.1 | 900 | 5 | 0.35 | 0.9941 | 0.9930 |
| K=3, p_act=0.1 | 1200 | 5 | 0.50 | 0.9926 | 0.9914 |
| K=3, p_act=0.1 | 1500 | 5 | 0.50 | 0.9946 | 0.9943 |
| K=3, p_act=0.1 | 1800 | 5 | 0.50 | 0.9948 | 0.9926 |
| K=6, -20 dB | 600 | 5 | 0.50 | 0.9963 | 0.9934 |
| K=6, -20 dB | 900 | 0 | 1.00 | 0.9931 | 0.9926 |
| K=6, -20 dB | 1200 | 0 | 1.00 | 0.9931 | 0.9918 |
| K=6, -20 dB | 1500 | 0 | 1.00 | 0.9938 | 0.9934 |
| K=6, -20 dB | 1800 | 0 | 1.00 | 0.9948 | 0.9930 |

## 关键数值闭环

- D3：固定单星功率下，$N_F=0\to30$ 的平均速率由 `0.0502` 增至 `0.1262` Gbps；固定集群总功率下则由 `0.0506` 降至 `0.0362` Gbps。
- D6：独立 RB 颜色相关系数为 `0.1693`，公共复用颜色相关系数为 `0.3664`。
- D7：半双工与全双工使用相同 SINR 覆盖事件，覆盖曲线逐点完全相同；全双工平均速率始终不低于半双工。
- D8：补充最大可见角、固定集群总功率和 ISL 门限敏感性，关闭目标清单中的剩余参数扫描缺口。

## 解释边界

- 通过表示当前模型内部数学、数值和交付物闭环，不等于真实星座外部验证。
- 部署图采用固定链路总发射功率下的带宽缩放热噪声；旧 Fig.S1-S8 保留固定参考噪声口径以维持版本兼容。
- D2 报告的是统计稳健的简约数量 $N_F^\dagger$，不是宣称存在脱离容差与业务目标的唯一精确最优数量。
- D2 的覆盖门限为 $-5$ dB；独立复验重新计算近最优速率集合，最终点再接受完整几何共享颜色相关干扰审计。
- 多随机种子审查单独报告边缘矩独立复验的离散选择范围；最终完整审计点还可能因相关干扰门禁而移动。

## 结论：PASS
