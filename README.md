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
