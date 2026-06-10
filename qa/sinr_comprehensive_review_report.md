# Comprehensive SINR And Reproduction-Figure QA Report

This report is generated from current files and executable validation gates.

## Acceptance Checks

| Check | Result |
|---|---:|
| `validation_gate` | PASS |
| `all_sinr_figures_exist` | PASS |
| `all_sinr_figure_pdfs_exist` | PASS |
| `eight_sinr_csv_files_exist` | PASS |
| `all_sinr_csv_values_finite` | PASS |
| `all_sinr_pdfs_exist` | PASS |
| `all_reproduction_ratio_errors_below_5_percent` | PASS |
| `activity_probability_sensitivity_present` | PASS |
| `network_proxy_is_explicit_and_spherical_proxy_present` | PASS |
| `monte_carlo_csvs_include_confidence_intervals` | PASS |
| `all_checks_pass` | PASS |

## Reproduction Figure Ratio Check

| Figure | Reference | Generated | Relative error |
|---|---:|---:|---:|
| `fig2` | 1.2914 | 1.2971 | 0.44% |
| `fig3` | 1.1246 | 1.1555 | 2.75% |
| `fig4` | 1.1543 | 1.1780 | 2.05% |
| `fig5` | 1.2326 | 1.2500 | 1.42% |
| `fig6` | 1.0974 | 1.1290 | 2.88% |
| `fig7` | 1.1391 | 1.1660 | 2.37% |
| `fig8` | 1.0222 | 1.0584 | 3.54% |

Each paper figure uses a dedicated source canvas. The acceptance threshold is 5% relative error after trimming white borders.

## SINR Validation

```json
{
  "finite_outputs": true,
  "coverage_ranges_valid": true,
  "e2e_not_above_access": true,
  "coordinated_improves_default_e2e": true,
  "noise_limited_has_zero_interference": true,
  "reuse_bandwidth_cost_applied": true,
  "gamma_vs_exact_rate_relative_error": 0.015554114001907652,
  "gamma_vs_exact_e2e_coverage_abs_error": 0.00275,
  "semi_vs_mc_lu_coverage_max_abs_error": 0.015715138663985273,
  "semi_lu_rate_gbps": 0.0010889248893729542,
  "mc_lu_rate_gbps": 0.0010638360760885017,
  "boundary_follower_interference_fraction_nl900": 0.0022042151739137617,
  "all_acceptance_checks_pass": true
}
```

## Model Closure

- Main model uses fixed total ground bandwidth and intra-cluster orthogonal resource blocks.
- Access coverage and end-to-end relay coverage are reported separately.
- Followers are tested for their own visibility, including followers whose parent leader is outside the visibility boundary.
- Frequency reuse, activity probability, and interference coupling gain are explicit parameters and are sensitivity-tested.
- Moment-matched semi-analytical results are checked against exact-geometry Monte Carlo.
- Primary Monte Carlo CSV outputs include 95% confidence intervals; Fig.S7 is a high-sample boundary-share estimator.

## Interpretation Limits

- `PASS` means the executable internal-consistency gates passed; it is not a claim of external validation against a real constellation.
- Original-paper figures are independently reproduced, not copied. Aspect ratios pass the 5% gate, but pixel identity is not claimed and Fig.7 retains a documented deterministic calibration.
- The SINR study remains a BPP snapshot model with scalar interference coupling, uniform resource allocation, and directional/orthogonal ISL assumptions.
- Network throughput and spherical spectral efficiency are comparison proxies because the model does not define a user point process, traffic arrivals, or full scheduling.

## Verdict: PASS
