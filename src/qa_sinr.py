"""Generate an auditable QA report for Fig.8 and the comprehensive SINR study."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qa_compare_figures import trim_white_border  # noqa: E402
from src.sinr_model import run_sinr_validation  # noqa: E402


def csv_is_finite(path: Path) -> bool:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return False
    for row in rows:
        for value in row.values():
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(number):
                return False
    return True


def image_ratio(path: Path) -> float:
    image = trim_white_border(Image.open(path).convert("RGB"))
    return image.width / image.height


def main() -> None:
    validation = run_sinr_validation()
    expected_figures = [ROOT / "figures" / "sinr" / f"figS{i}_{suffix}.png" for i, suffix in [
        (1, "resource_model_coverage"),
        (2, "access_vs_e2e"),
        (3, "rate_resource_models"),
        (4, "network_throughput"),
        (5, "coordination_sensitivity"),
        (6, "semi_analytical_validation"),
        (7, "boundary_correction"),
        (8, "rate_reliability_frontier"),
    ]]
    expected_data = sorted((ROOT / "figures" / "sinr_data").glob("figS*.csv"))
    expected_figure_pdfs = [path.with_suffix(".pdf") for path in expected_figures]
    expected_docs = [
        ROOT / "theory" / "sinr_comprehensive_derivation.pdf",
        ROOT / "theory" / "sinr_results_analysis.pdf",
    ]
    reproduction_ratios = {}
    for index in range(2, 9):
        name = f"fig{index}"
        ref_ratio = image_ratio(ROOT / "figures" / "reference" / f"{name}_reference.png")
        gen_ratio = image_ratio(ROOT / "figures" / "generated" / f"{name}.png")
        reproduction_ratios[name] = {
            "reference": ref_ratio,
            "generated": gen_ratio,
            "relative_error": abs(gen_ratio - ref_ratio) / ref_ratio,
        }
    s5_text = (ROOT / "figures" / "sinr_data" / "figS5_coordination_sensitivity.csv").read_text(encoding="utf-8")
    s4_header = (ROOT / "figures" / "sinr_data" / "figS4_network_throughput.csv").read_text(encoding="utf-8").splitlines()[0]
    ci_files = [path for path in expected_data if not path.name.startswith("figS7_")]
    checks = {
        "validation_gate": bool(validation["all_acceptance_checks_pass"]),
        "all_sinr_figures_exist": all(path.exists() and path.stat().st_size > 0 for path in expected_figures),
        "all_sinr_figure_pdfs_exist": all(path.exists() and path.stat().st_size > 0 for path in expected_figure_pdfs),
        "eight_sinr_csv_files_exist": len(expected_data) == 8,
        "all_sinr_csv_values_finite": len(expected_data) == 8 and all(csv_is_finite(path) for path in expected_data),
        "all_sinr_pdfs_exist": all(path.exists() and path.stat().st_size > 0 for path in expected_docs),
        "all_reproduction_ratio_errors_below_5_percent": all(item["relative_error"] < 0.05 for item in reproduction_ratios.values()),
        "activity_probability_sensitivity_present": "\nactivity," in s5_text,
        "network_proxy_is_explicit_and_spherical_proxy_present": "network_throughput" in s4_header and "spherical_spectral_efficiency_proxy" in s4_header,
        "monte_carlo_csvs_include_confidence_intervals": all(
            "ci_low" in path.read_text(encoding="utf-8").splitlines()[0]
            and "ci_high" in path.read_text(encoding="utf-8").splitlines()[0]
            for path in ci_files
        ),
    }
    checks["all_checks_pass"] = all(checks.values())
    payload = {
        "checks": checks,
        "reproduction_figure_ratios": reproduction_ratios,
        "sinr_validation": validation,
    }
    report = ROOT / "qa" / "sinr_comprehensive_review_report.md"
    lines = [
        "# Comprehensive SINR And Reproduction-Figure QA Report",
        "",
        "This report is generated from current files and executable validation gates.",
        "",
        "## Acceptance Checks",
        "",
        "| Check | Result |",
        "|---|---:|",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Reproduction Figure Ratio Check",
            "",
            "| Figure | Reference | Generated | Relative error |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, values in reproduction_ratios.items():
        lines.append(
            f"| `{name}` | {values['reference']:.4f} | {values['generated']:.4f} | {values['relative_error']:.2%} |"
        )
    lines.extend(
        [
            "",
            "Each paper figure uses a dedicated source canvas. The acceptance threshold is 5% relative error after trimming white borders.",
            "",
            "## SINR Validation",
            "",
            "```json",
            json.dumps(validation, indent=2),
            "```",
            "",
            "## Model Closure",
            "",
            "- Main model uses fixed total ground bandwidth and intra-cluster orthogonal resource blocks.",
            "- Access coverage and end-to-end relay coverage are reported separately.",
            "- Followers are tested for their own visibility, including followers whose parent leader is outside the visibility boundary.",
            "- Frequency reuse, activity probability, and interference coupling gain are explicit parameters and are sensitivity-tested.",
            "- Moment-matched semi-analytical results are checked against exact-geometry Monte Carlo.",
            "- Primary Monte Carlo CSV outputs include 95% confidence intervals; Fig.S7 is a high-sample boundary-share estimator.",
            "",
            "## Interpretation Limits",
            "",
            "- `PASS` means the executable internal-consistency gates passed; it is not a claim of external validation against a real constellation.",
            "- Original-paper figures are independently reproduced, not copied. Aspect ratios pass the 5% gate, but pixel identity is not claimed and Fig.7 retains a documented deterministic calibration.",
            "- The SINR study remains a BPP snapshot model with scalar interference coupling, uniform resource allocation, and directional/orthogonal ISL assumptions.",
            "- Network throughput and spherical spectral efficiency are comparison proxies because the model does not define a user point process, traffic arrivals, or full scheduling.",
            "",
            f"## Verdict: {'PASS' if checks['all_checks_pass'] else 'FAIL'}",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not checks["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
