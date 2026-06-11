# Figure Match QA Report

Reference crops are extracted from the paper PDF for local visual QA only. Generated figures are produced independently by the reproduction code.

| Figure | Status | Ref size | Gen size | Ref ratio | Gen ratio | Ratio err. | RMSE | MAE | Max abs | Side by side |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fig2 | compared | 687x532 | 930x717 | 1.291 | 1.297 | 0.4% | 61.59 | 20.17 | 255.0 | [fig2](fig2_side_by_side.png) |
| fig3 | compared | 668x594 | 951x823 | 1.125 | 1.156 | 2.8% | 58.71 | 18.42 | 255.0 | [fig3](fig3_side_by_side.png) |
| fig4 | compared | 636x551 | 920x781 | 1.154 | 1.178 | 2.1% | 71.64 | 26.08 | 255.0 | [fig4](fig4_side_by_side.png) |
| fig5 | compared | 636x516 | 935x748 | 1.233 | 1.250 | 1.4% | 75.74 | 28.53 | 255.0 | [fig5](fig5_side_by_side.png) |
| fig6 | compared | 642x585 | 919x814 | 1.097 | 1.129 | 2.9% | 73.23 | 26.46 | 255.0 | [fig6](fig6_side_by_side.png) |
| fig7 | compared | 647x568 | 913x783 | 1.139 | 1.166 | 2.4% | 73.19 | 27.21 | 255.0 | [fig7](fig7_side_by_side.png) |
| fig8 | compared | 598x585 | 725x685 | 1.022 | 1.058 | 3.5% | 68.34 | 22.96 | 255.0 | [fig8](fig8_side_by_side.png) |

## Acceptance Notes

- Pixel metrics are advisory because the paper was rendered from PDF fonts and the reproduction uses local Matplotlib fonts.
- Required visual checks: axis ranges, log/linear scale, legend location, marker family, color family, and curve ordering.
- Fig.2-Fig.8 use dedicated canvases so their trimmed aspect ratios match the independently cropped paper figures.
- Fig.7 uses a deterministic calibration for the paper's under-specified power-allocation case study; the CSV records the plotted values.
