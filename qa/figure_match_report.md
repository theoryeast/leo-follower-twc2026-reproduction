# Figure Match QA Report

Reference crops are extracted from the paper PDF for local visual QA only. Generated figures are produced independently by the reproduction code.

| Figure | Status | Ref size | Gen size | RMSE | MAE | Max abs | Side by side |
|---|---:|---:|---:|---:|---:|---:|---|
| fig2 | compared | 687x532 | 930x694 | 61.73 | 20.13 | 255.0 | [fig2](qa/fig2_side_by_side.png) |
| fig3 | compared | 668x594 | 951x700 | 61.55 | 19.84 | 255.0 | [fig3](qa/fig3_side_by_side.png) |
| fig4 | compared | 636x551 | 920x693 | 76.29 | 29.01 | 255.0 | [fig4](qa/fig4_side_by_side.png) |
| fig5 | compared | 636x516 | 935x693 | 76.78 | 29.22 | 255.0 | [fig5](qa/fig5_side_by_side.png) |
| fig6 | compared | 642x585 | 919x685 | 75.91 | 28.18 | 255.0 | [fig6](qa/fig6_side_by_side.png) |
| fig7 | compared | 647x568 | 913x693 | 73.50 | 27.24 | 255.0 | [fig7](qa/fig7_side_by_side.png) |
| fig8 | compared | 598x585 | 935x685 | 65.32 | 21.21 | 255.0 | [fig8](qa/fig8_side_by_side.png) |

## Acceptance Notes

- Pixel metrics are advisory because the paper was rendered from PDF fonts and the reproduction uses local Matplotlib fonts.
- Required visual checks: axis ranges, log/linear scale, legend location, marker family, color family, and curve ordering.
- Fig.7 uses a deterministic calibration for the paper's under-specified power-allocation case study; the CSV records the plotted values.
