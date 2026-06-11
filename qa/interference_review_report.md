# Interference Extension Review Report

Generated on 2026-05-30 for branch `interference-extension`.

## Scope

This review covers the new dense same-frequency inter-cluster interference model:

- typical user is served by the nearest leader cluster;
- serving leader/followers are desired branches;
- all visible non-serving leaders/followers are same-frequency downlink interferers;
- leader-follower ISL remains directional or orthogonal and is not included in the ground interference bottleneck.

The original IEEE PDF and reference crops remain local-only and are not required for this extension review.

## Commands Run

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\reproduce_interference_figures.py' --all --mode final
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' -m py_compile 'src\leo_follower_model.py' 'src\reproduce_figures.py' 'src\qa_compare_figures.py' 'src\interference_model.py' 'src\reproduce_interference_figures.py'
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' -c "from src.interference_model import run_interference_sanity_checks; import json; print(json.dumps(run_interference_sanity_checks(), indent=2, ensure_ascii=False))"
Push-Location theory
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_results_analysis.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_results_analysis.tex'
Pop-Location
```

## Mathematical Consistency Checks

| Check | Result |
|---|---:|
| Finite outputs, no NaN/Inf in sanity paths | PASS |
| No-interference simulation recovers no-interference Monte Carlo baseline | PASS |
| Relative error versus no-interference Monte Carlo | 0.0141 |
| `N_F=0` same-frequency case remains positive-rate leader-only network | PASS |
| Mean INR increases from `N_F=0` to `N_F=10` at `N_L=900` | PASS |
| Mean INR increases from `N_L=900` to `N_L=1200` at `N_F=10` | PASS |
| Coverage probabilities remain in `[0,1]` | PASS |

Sanity output:

```json
{
  "finite_outputs": true,
  "no_interference_rate_gbps": 0.26116089293068,
  "baseline_middle_rate_gbps": 0.35309072909241973,
  "baseline_mc_rate_gbps": 0.25752663634666,
  "no_interference_relative_error": 0.26035754718917453,
  "no_interference_relative_error_vs_mc": 0.014112158010435463,
  "no_interference_recovers_mc": true,
  "nf0_mean_inr": 7.299492293726671,
  "nf10_mean_inr": 30.10552753930373,
  "nl1200_nf10_mean_inr": 40.23885555280648,
  "nf_increases_interference": true,
  "nl_increases_interference": true,
  "nf0_rate_positive": true,
  "coverage_probability_valid": true
}
```

The no-interference comparison is made against `average_rate_cluster_monte_carlo`, not against the Corollary-2 middle approximation. The middle approximation remains useful for plotting and parameter scans, but it is not the exact same random estimator.

## Semi-Analytical Versus Monte Carlo Spot Checks

Mean-field INR was compared with direct Monte Carlo aggregate interference on three representative cases:

| `N_L` | `N_F` | Mean-field INR | MC mean INR | Relative error |
|---:|---:|---:|---:|---:|
| 600 | 0 | 4.6213 | 4.5886 | 0.0071 |
| 900 | 10 | 29.8391 | 29.8918 | 0.0018 |
| 1500 | 20 | 90.3694 | 90.6021 | 0.0026 |

The checked errors are below 1%, so the mean-field INR is reliable for the trend figures and heatmap. Monte Carlo remains the primary estimator for Fig.I2 and Fig.I3.

## Figure And Data Artifacts

All expected files exist:

- `figures/interference/figI1_mean_inr.{pdf,png}`
- `figures/interference/figI2_sinr_coverage.{pdf,png}`
- `figures/interference/figI3_cluster_rate.{pdf,png}`
- `figures/interference/figI4_network_throughput.{pdf,png}`
- `figures/interference/figI5_nf_nl_heatmap.{pdf,png}`
- `figures/interference_data/figI1_mean_inr.csv`
- `figures/interference_data/figI2_sinr_coverage.csv`
- `figures/interference_data/figI3_cluster_rate.csv`
- `figures/interference_data/figI4_network_throughput.csv`
- `figures/interference_data/figI5_nf_nl_heatmap.csv`
- `theory/interference_derivation.pdf`
- `theory/interference_results_analysis.pdf`

Visual inspection passed: axes, legends, markers, confidence intervals, and heatmap colorbar are readable at single-column size.

## Result Anchors

- Fig.I1: at `N_L=1500`, mean INR rises from `10.92 dB` for `N_F=0` to `17.11 dB` for `N_F=10` and `21.12 dB` for `N_F=30`.
- Fig.I2: with no inter-cluster interference and `N_F=10`, coverage is about `0.976` at `-5 dB`; with same-frequency interference and `N_F=10`, coverage is already near zero at `-10 dB`.
- Fig.I3: noise-limited cluster rate grows from `0.079 Gbps` to `1.003 Gbps` as `N_F` goes from `0` to `30`; same-frequency interference compresses the rate to roughly `0.0083-0.0093 Gbps`.
- Fig.I4: network throughput still grows with `N_L`, but slowly, indicating interference-limited spatial reuse.
- Fig.I5: the best mean-field cluster rate in the scanned grid often occurs at the largest `N_F`, but this is not a blanket recommendation because Fig.I2 shows severe coverage loss.

## Remaining Limitations

- The extension assumes full same-frequency reuse. Frequency reuse, beam scheduling, and coordinated muting are deliberately left for the next research step.
- The follower interference simulation uses representative follower sampling per cluster and scales by `N_F`; mean INR spot checks show this is accurate for the plotted trends.
- The heatmap uses a deterministic mean-field INR penalty for speed. It should be refined with larger Monte Carlo runs if the final paper needs exact confidence intervals over the full `N_L`--`N_F` plane.
- ISL interference is excluded by assumption because leader-follower links are modeled as highly directional or orthogonal.

## Verdict

PASS. The new interference model, figures, data, TeX derivation, and TeX result analysis are internally consistent and reproducible from the recorded commands.
