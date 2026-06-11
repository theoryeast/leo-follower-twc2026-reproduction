"""Crop reference figures from the paper and compare generated reproductions."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "[032-TWC-2026]Coverage_and_Rate_Analysis_of_Follower-Based_LEO_Satellite_Networks_A_Stochastic_Geometry_Approach.pdf"
GENERATED = ROOT / "figures" / "generated"
REFERENCE = ROOT / "figures" / "reference"
QA = ROOT / "qa"


# Normalized boxes over rendered letter pages.  They intentionally crop the
# axes region rather than the caption, because generated figures are standalone.
FIGURE_BOXES = {
    "fig2": (6, (0.520, 0.075, 0.895, 0.295)),
    "fig3": (7, (0.105, 0.075, 0.462, 0.322)),
    "fig4": (7, (0.548, 0.074, 0.888, 0.309)),
    "fig5": (7, (0.548, 0.394, 0.888, 0.629)),
    "fig6": (8, (0.112, 0.073, 0.455, 0.315)),
    "fig7": (8, (0.112, 0.397, 0.458, 0.640)),
    "fig8": (9, (0.125, 0.078, 0.445, 0.320)),
}


def find_pdftoppm() -> str:
    found = shutil.which("pdftoppm")
    if found:
        return found
    miktex = Path(r"D:\MiKTeX\texmfs\install\miktex\bin\x64\pdftoppm.exe")
    if miktex.exists():
        return str(miktex)
    raise FileNotFoundError("pdftoppm not found")


def render_page(page: int, dpi: int = 220) -> Path:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    out_prefix = REFERENCE / f"paper_page_{page:02d}_{dpi}dpi"
    png = out_prefix.with_name(out_prefix.name + f"-{page:02d}.png")
    if png.exists():
        return png
    cmd = [find_pdftoppm(), "-f", str(page), "-l", str(page), "-png", "-r", str(dpi), str(PAPER), str(out_prefix)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    if not png.exists():
        candidates = sorted(REFERENCE.glob(f"{out_prefix.name}-*.png"))
        if candidates:
            return candidates[0]
    return png


def crop_reference(name: str) -> Path:
    page, box = FIGURE_BOXES[name]
    page_png = render_page(page)
    img = Image.open(page_png).convert("RGB")
    w, h = img.size
    left, top, right, bottom = box
    crop = img.crop((round(left * w), round(top * h), round(right * w), round(bottom * h)))
    out = REFERENCE / f"{name}_reference.png"
    crop.save(out)
    return out


def trim_white_border(img: Image.Image, tolerance: int = 248) -> Image.Image:
    arr = np.asarray(img.convert("RGB"))
    mask = np.any(arr < tolerance, axis=2)
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    pad = 4
    left = max(int(xs.min()) - pad, 0)
    right = min(int(xs.max()) + pad + 1, img.width)
    top = max(int(ys.min()) - pad, 0)
    bottom = min(int(ys.max()) + pad + 1, img.height)
    return img.crop((left, top, right, bottom))


def compare_pair(name: str) -> dict[str, float | str]:
    ref_path = crop_reference(name)
    gen_path = GENERATED / f"{name}.png"
    if not gen_path.exists():
        return {"figure": name, "status": "missing generated image"}
    ref = trim_white_border(Image.open(ref_path).convert("RGB"))
    gen = trim_white_border(Image.open(gen_path).convert("RGB"))
    ref_ratio = ref.width / ref.height
    gen_ratio = gen.width / gen.height
    gen_resized = gen.resize(ref.size, Image.Resampling.LANCZOS)
    ref_arr = np.asarray(ref, dtype=np.float32)
    gen_arr = np.asarray(gen_resized, dtype=np.float32)
    diff = gen_arr - ref_arr
    rmse = float(np.sqrt(np.mean(diff * diff)))
    mae = float(np.mean(np.abs(diff)))
    max_abs = float(np.max(np.abs(diff)))

    QA.mkdir(parents=True, exist_ok=True)
    diff_img = ImageChops.difference(ref, gen_resized)
    enhanced = diff_img.point(lambda px: min(255, px * 4))
    composite = Image.new("RGB", (ref.width * 3 + 20, ref.height), "white")
    composite.paste(ref, (0, 0))
    composite.paste(gen_resized, (ref.width + 10, 0))
    composite.paste(enhanced, (ref.width * 2 + 20, 0))
    draw = ImageDraw.Draw(composite)
    draw.text((5, 5), "paper crop", fill=(0, 0, 0))
    draw.text((ref.width + 15, 5), "generated", fill=(0, 0, 0))
    draw.text((ref.width * 2 + 25, 5), "diff x4", fill=(0, 0, 0))
    composite_path = QA / f"{name}_side_by_side.png"
    composite.save(composite_path)
    return {
        "figure": name,
        "status": "compared",
        "reference_size": f"{ref.width}x{ref.height}",
        "generated_size": f"{gen.width}x{gen.height}",
        "reference_ratio": ref_ratio,
        "generated_ratio": gen_ratio,
        "ratio_relative_error": abs(gen_ratio - ref_ratio) / ref_ratio,
        "rmse": rmse,
        "mae": mae,
        "max_abs": max_abs,
        "side_by_side": composite_path.name,
    }


def write_report(rows: list[dict[str, float | str]]) -> None:
    QA.mkdir(parents=True, exist_ok=True)
    report = QA / "figure_match_report.md"
    lines = [
        "# Figure Match QA Report",
        "",
        "Reference crops are extracted from the paper PDF for local visual QA only. Generated figures are produced independently by the reproduction code.",
        "",
        "| Figure | Status | Ref size | Gen size | Ref ratio | Gen ratio | Ratio err. | RMSE | MAE | Max abs | Side by side |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        if row.get("status") != "compared":
            lines.append(f"| {row['figure']} | {row['status']} | | | | | | | | | |")
            continue
        lines.append(
            "| {figure} | {status} | {reference_size} | {generated_size} | {reference_ratio:.3f} | {generated_ratio:.3f} | {ratio_relative_error:.1%} | {rmse:.2f} | {mae:.2f} | {max_abs:.1f} | [{figure}]({side_by_side}) |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Acceptance Notes",
            "",
            "- Pixel metrics are advisory because the paper was rendered from PDF fonts and the reproduction uses local Matplotlib fonts.",
            "- Required visual checks: axis ranges, log/linear scale, legend location, marker family, color family, and curve ordering.",
            "- Fig.2-Fig.8 use dedicated canvases so their trimmed aspect ratios match the independently cropped paper figures.",
            "- Fig.7 uses a deterministic calibration for the paper's under-specified power-allocation case study; the CSV records the plotted values.",
        ]
    )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Compare Fig.2-Fig.8")
    parser.add_argument("--fig", choices=sorted(FIGURE_BOXES), action="append")
    args = parser.parse_args()
    selected = sorted(FIGURE_BOXES) if args.all or not args.fig else args.fig
    rows = []
    for name in selected:
        print(f"Comparing {name}...")
        rows.append(compare_pair(name))
    write_report(rows)
    print(f"QA report written to {QA / 'figure_match_report.md'}")


if __name__ == "__main__":
    main()
