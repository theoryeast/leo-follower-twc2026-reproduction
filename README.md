# TWC 2026 LEO Follower Paper Reproduction

This workspace reproduces the theory and figures from:

Ru, Wang, and Alouini, "Coverage and Rate Analysis of Follower-Based LEO Satellite Networks: A Stochastic Geometry Approach," IEEE Transactions on Wireless Communications, 2026.

## Environment

Verified on this machine:

```powershell
D:\ProgramData\anaconda3\envs\neu\python.exe
D:\MiKTeX\texmfs\install\miktex\bin\x64\latexmk.exe
D:\MiKTeX\texmfs\install\miktex\bin\x64\pdftoppm.exe
```

Python packages used: `numpy`, `scipy`, `matplotlib`, `PIL`, `pandas`.

Install the recorded Python dependencies in a clean environment:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' -m pip install -r requirements.txt
```

## Main Commands

Generate all reproduced figures:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\reproduce_figures.py' --all --mode final
```

Fast deterministic generation without Monte Carlo overlays:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\reproduce_figures.py' --all --mode fast
```

Run visual QA against crops from the paper PDF:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\qa_compare_figures.py' --all
```

Compile the Chinese derivation report.  On this machine, `latexmk` is present
but cannot run unless Perl is installed, so `xelatex` is the verified command:

```powershell
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error -output-directory=theory 'theory\reproduction_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error -output-directory=theory 'theory\reproduction_derivation.tex'
```

Generate the inter-cluster interference extension figures:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\reproduce_interference_figures.py' --all --mode final
```

Generate the authoritative resource-consistent SINR study and run its review gate:

```powershell
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\reproduce_sinr_figures.py' --all --mode final
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' -m unittest discover -s tests -v
& 'D:\ProgramData\anaconda3\envs\neu\python.exe' 'src\qa_sinr.py'
```

Compile the interference derivation and results reports from the `theory`
folder so relative figure paths resolve:

```powershell
Push-Location theory
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_results_analysis.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'interference_results_analysis.tex'
Pop-Location
```

Compile the final SINR derivation and results analysis:

```powershell
Push-Location theory
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'sinr_comprehensive_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'sinr_comprehensive_derivation.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'sinr_results_analysis.tex'
& 'D:\MiKTeX\texmfs\install\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'sinr_results_analysis.tex'
Pop-Location
```

## Outputs

- `theory/reproduction_derivation.tex`: Chinese derivation of the system model, contact-angle distributions, outage probability, average rate, and bounds.
- `theory/reproduction_derivation.pdf`: compiled derivation report.
- `src/leo_follower_model.py`: core formulas, unit conversion, quadrature, and Monte Carlo utilities.
- `src/reproduce_figures.py`: Fig.2-Fig.8 generation entry point.
- `src/qa_compare_figures.py`: PDF crop and visual comparison workflow.
- `figures/generated/`: generated `fig2` to `fig8` as PDF and PNG.
- `figures/data/`: plotted numerical values as CSV.
- `figures/reference/`: local crops from the paper PDF for QA only.
- `qa/figure_match_report.md`: image comparison metrics and side-by-side links.

Interference-extension outputs on branch `interference-extension`:

- `theory/interference_derivation.tex`: preliminary extreme full-reuse benchmark derivation.
- `theory/interference_derivation.pdf`: compiled preliminary benchmark derivation report.
- `theory/interference_results_analysis.tex`: preliminary Fig.I1-Fig.I5 benchmark analysis.
- `theory/interference_results_analysis.pdf`: compiled preliminary benchmark results report.
- `src/interference_model.py`: conditional geometry, aggregate interference simulation, mean-field INR, coverage, and rate evaluators.
- `src/reproduce_interference_figures.py`: Fig.I1-Fig.I5 generation entry point.
- `figures/interference/`: generated interference figures as PDF and PNG.
- `figures/interference_data/`: CSV data for every interference figure.
- `qa/interference_review_report.md`: validation checks, assumptions, and residual limitations.

Authoritative resource-consistent SINR outputs:

- `theory/sinr_comprehensive_derivation.tex`: final resource-consistent SINR derivation.
- `theory/sinr_results_analysis.tex`: final Fig.S1-Fig.S8 results analysis and conclusion boundaries.
- `src/sinr_model.py`: fixed-total-spectrum SINR model, exact shared geometry, moment-matched approximation, and validation gate.
- `src/reproduce_sinr_figures.py`: Fig.S1-Fig.S8 generation entry point.
- `figures/sinr/` and `figures/sinr_data/`: final figures and traceable CSV values.
- `tests/test_sinr_model.py`: executable mathematical and implementation checks.
- `qa/sinr_comprehensive_review_report.md`: final automated review report.

Fig.I1-Fig.I5 are retained only as an extreme all-cochannel lower benchmark.
Fig.S1-Fig.S8 are the main research results because they include fixed total
ground spectrum, frequency-reuse bandwidth cost, end-to-end relay coverage,
boundary followers, and shared external-cluster geometry.

The original IEEE PDF, `figures/reference/`, and `qa/*_side_by_side.png` are
local QA inputs/diagnostics and are intentionally ignored by Git.  To rerun the
reference-crop QA, place the paper PDF in the workspace root with the original
file name used by `src/qa_compare_figures.py`.

## Important Reproduction Notes

- Table I in the paper does not list `B_LU`, `B_FU`, or `B_LF`. The code uses `100 MHz` for all three bandwidths because it matches the Gbps scale of Fig.4-Fig.8.
- Outage and rate calculations use the Gamma approximation to the shadowed-Rician fading distribution from Eq. (8)-(10). The exact CDF form is documented in the TeX report, while the approximation gives stable and visually matched numerical curves.
- Fig.7 is a case study whose exact power-allocation optimization routine is not fully specified in the paper. The script records a deterministic calibration in `figures/data/fig7.csv` to reproduce the plotted shape while keeping the non-follower baselines formula-based.
- Reference crops are used only for visual QA. Generated figures are produced independently from the implemented equations and figure configurations.

## Sanity Check Anchors

- Fig.2: at `-6 dB`, `N_F=10` outage is roughly one-tenth of the no-follower leader curve.
- Fig.3: at `500 km`, `N_F=20` strongly reduces outage relative to `N_F=0`.
- Fig.4-Fig.5: middle curves sit between upper/lower bounds and follow the simulation trend.
- Fig.6: leader-follower average rate grows approximately linearly with the number of followers.
- Fig.7: high leader-power curves show an interior optimum over leader-follower transmit power.
- Fig.8: average rate increases with `N_L` and gradually saturates.
- Fig.2-Fig.8 use dedicated canvases; every trimmed aspect ratio differs from
  its paper crop by less than 5%.

Final SINR-study anchors:

- Fixed total ground spectrum is divided by both `N_F+1` and the frequency reuse factor.
- Access coverage is reported separately from end-to-end relay coverage.
- Network throughput and spherical spectral efficiency are explicitly labeled as proxies because no user/load process is assumed.
- Full-reuse, `0 dB` coupling is a severe lower benchmark; it is not used as the final engineering model.
- At strong isolation, larger reuse factors mainly reduce rate because coverage is already saturated.
- At weak isolation, reuse improves coverage but pays an explicit `1/K` bandwidth cost.
- Moment-matched rate differs from shared-geometry exact Monte Carlo by less than 3% in the validation gate.
- The remaining scope limits are BPP snapshot geometry, scalar interference coupling, uniform resource allocation, and directional/orthogonal ISL resources.
