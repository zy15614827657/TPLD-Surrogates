"""Build traceable GitHub showcase assets from the existing local result exports.

This script only reads source experiments. It does not train or run models.
Scientific panels are cropped/resized, never retouched or interpolated in time.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets"
RESULTS = REPO / "results"
NAVY = "#0d2532"
MUTED = "#5a7281"
TEAL = "#4ddac6"
WIDTH, HEIGHT = 1200, 560


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, bold=False):
    candidates = [Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
                  Path(matplotlib.get_data_path()) / "fonts/ttf" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError("A TrueType font is required for readable scientific labels")


def card(title, subtitle, footer, tag):
    im = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, WIDTH, 96), fill=NAVY)
    draw.rectangle((0, 0, 7, 96), fill=TEAL)
    draw.text((28, 13), title, fill="white", font=font(27, True))
    draw.text((29, 53), subtitle, fill="#bed3df", font=font(19))
    draw.line((28, 504, 1172, 504), fill="#dbe5eb", width=1)
    draw.text((29, 516), footer, fill=MUTED, font=font(17))
    # The task label travels with the GIF when shared outside the README.
    box = draw.textbbox((0, 0), tag, font=font(16, True))
    x = WIDTH - (box[2] - box[0]) - 46
    draw.rounded_rectangle((x - 12, 18, WIDTH - 24, 47), radius=9, fill="#1b4c53")
    draw.text((x, 21), tag, fill="#a2eedc", font=font(16, True))
    return im


def fit(im, width, height):
    im = im.copy()
    im.thumbnail((width, height), Image.Resampling.LANCZOS)
    return im


def paste_center(target, panel, bounds):
    x, y, w, h = bounds
    p = fit(panel, w, h)
    target.paste(p, (x + (w - p.width) // 2, y + (h - p.height) // 2))


def save_gif(frames, path, durations):
    # One palette for all frames avoids frame-to-frame palette flicker.
    contact = Image.new("RGB", (300, 140 * len(frames)), "white")
    for i, frame in enumerate(frames):
        contact.paste(frame.resize((300, 140)), (0, i * 140))
    palette = contact.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], loop=0,
                    duration=durations, disposal=2, optimize=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Directory containing 100_Car_Crash, 131_bumper and Flow")
    args = parser.parse_args()
    root = args.source_root.resolve()
    sources = {}
    transforms = []
    for name in ["car-crash", "bumper", "flow"]:
        (ASSETS / name).mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(exist_ok=True)

    def source(path):
        rel = path.relative_to(root).as_posix()
        sources[rel] = {"path_relative_to_source_root": rel,
                        "sha256": digest(path), "bytes": path.stat().st_size}
        return path

    def copied(src, dest):
        shutil.copy2(source(src), dest)
        transforms.append({"output": dest.relative_to(REPO).as_posix(),
                           "source": src.relative_to(root).as_posix(), "operation": "byte-identical copy"})

    crash = root / "100_Car_Crash/Car_Crash_1026"
    bumper = root / "131_bumper/Bumper_Visualization"
    flow = root / "Flow/analysis"
    car_case, bumper_case = "yaris_x00063", "Run227"
    animation_jobs = [
        (crash / "figures" / car_case, "car-crash", (0, 90, 2160, 666),
         "VEHICLE CRASH", car_case, "136,727 BIW nodes | displacement magnitude (mm)"),
        (bumper / "figures/stage2" / bumper_case, "bumper", (0, 100, 1920, 574),
         "BUMPER IMPACT", bumper_case, "13,676 nodes | displacement magnitude (source units)"),
    ]
    for folder, name, crop, title, case, footer in animation_jobs:
        paths = sorted(folder.glob("frame_*_displacement.png"))
        expected = 13 if name == "car-crash" else 11
        if len(paths) != expected:
            raise ValueError(f"Expected {expected} scientific frames, found {len(paths)} in {folder}")
        frames = []
        for i, path in enumerate(paths):
            source(path)
            stamp = f"t = {i * 10:03d} ms" if name == "car-crash" else f"t = {i * 10:03d} (source time)"
            im = card(title, f"{case}   /   {stamp}   /   frame {i+1:02d} of {expected}", footer, "PREDICTION")
            with Image.open(path) as raw:
                panel = raw.convert("RGB").crop(crop)
                paste_center(im, panel, (22, 105, 1156, 385))
            frames.append(im)
        dest = ASSETS / name
        save_gif(frames, dest / "prediction.gif", [180] * (len(frames) - 1) + [1000])
        frames[-1].save(dest / "preview.png", optimize=True)
        copied(paths[-1], dest / "full-comparison.png")
        if name == "bumper":
            copied(bumper / "curves/stage2" / f"{case}_r2.png", dest / "r2-curve.png")
        transforms.append({"output": f"assets/{name}/prediction.gif", "case": case,
                           "sources": [p.relative_to(root).as_posix() for p in paths],
                           "crop_box_xyxy": crop, "frames": len(frames),
                           "operation": "first-view prediction/truth/error panels; Lanczos thumbnail; shared 256-color GIF palette",
                           "time_policy": "all saved frames, forward order, no temporal interpolation; slowed for viewing",
                           "selection": "illustrative case selected for visualization, not an aggregate metric"})

    # Frozen Epoch-71 comparison: keep the original full image alongside the compact card.
    sample = flow / "test_all_stage1_20261029/cases/nurbs/87/Re_874"
    sample_meta = read_json(source(sample / "comparison_metadata.json"))
    raw_path = source(sample / "FPO_test_truth_reconstruction_error_2D_preview.png")
    with Image.open(raw_path) as raw:
        im = card("FLOW FIELD RECONSTRUCTION", "nurbs/87/Re_874   /   Epoch 71   /   final saved frame",
                  "True field enters the encoder. This panel measures AE reconstruction.", "RECONSTRUCTION")
        draw = ImageDraw.Draw(im)
        for x, label in [(70, "GROUND TRUTH"), (450, "AE RECONSTRUCTION"), (835, "ABSOLUTE ERROR")]:
            draw.text((x, 112), label, fill=NAVY, font=font(19, True))
        for y, box in [(148, (55, 166, 1850, 367)), (321, (55, 425, 1850, 626))]:
            paste_center(im, raw.crop(box).convert("RGB"), (25, y, 1150, 171))
        im.save(ASSETS / "flow/reconstruction-preview.png", optimize=True)
    copied(sample / "FPO_test_truth_reconstruction_error_2D.png", ASSETS / "flow/reconstruction-full.png")
    transforms.append({"output": "assets/flow/reconstruction-preview.png",
                       "source": raw_path.relative_to(root).as_posix(),
                       "operation": "u and v rows cropped and resized; p retained in full-comparison image",
                       "crop_boxes_xyxy": [[55,166,1850,367],[55,425,1850,626]],
                       "checkpoint_epoch": 71, "task": "true-field-conditioned AE reconstruction"})

    # Render the four actual stored reference snapshots; never invent intermediate states.
    reference = source(flow / "flowbench_20261028/FPO_representative.npz")
    reference_meta = read_json(source(flow / "flowbench_20261028/representative_metadata.json"))
    case_meta = next(c for c in reference_meta["cases"] if c["dataset"] == "FPO_NS_2D_1024x256")
    with np.load(reference, allow_pickle=False) as z:
        fields, mask, indices = z["data"], z["mask"], z["frame_indices"]
    assert list(indices) == case_meta["frame_indices_zero_based"]
    solid = mask < .5
    speed = np.linalg.norm(fields[..., :2], axis=-1)
    speed_max = float(speed[:, ~solid].max())
    pressure_abs = float(np.abs(fields[..., 2][:, ~solid]).max())
    frames = []
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    for i, index in enumerate(indices):
        im = card("FLOW AROUND COMPLEX GEOMETRY", f"harmonics/1   /   Re = 603   /   saved frame {index+1:03d} of 242",
                  "Reference simulation | 4 sampled snapshots | stored units; no physical time assigned", "REFERENCE DATA")
        fig, axis = plt.subplots(figsize=(11.5, 3.8), dpi=100)
        fig.subplots_adjust(left=.055, right=.94, bottom=.15, top=.90)
        for ax, values, name, cmap, norm in [
            (axis, speed[i], "Speed magnitude |V|", "viridis", matplotlib.colors.Normalize(0, speed_max)),
        ]:
            palette = plt.get_cmap(cmap).copy()
            palette.set_bad("#cbd5e1")
            picture = ax.imshow(np.ma.masked_where(solid, values), origin="lower", extent=(4,20,6,10),
                                interpolation="nearest", cmap=palette, norm=norm, aspect="equal")
            ax.set_title(name, loc="left", fontsize=12, pad=3)
            ax.set_ylabel("y")
            ax.set_xlabel("x", labelpad=0)
            fig.colorbar(picture, ax=ax, pad=.025, fraction=.025, aspect=15)
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", facecolor="white")
        plt.close(fig)
        buffer.seek(0)
        with Image.open(buffer) as panel:
            paste_center(im, panel.convert("RGB"), (20, 100, 1160, 395))
        frames.append(im)
    save_gif(frames, ASSETS / "flow/reference-snapshots.gif", [850, 850, 850, 1500])
    frames[-1].save(ASSETS / "flow/reference-preview.png", optimize=True)
    copied(flow / "flowbench_20261028/fpo_time_sequence.png", ASSETS / "flow/reference-time-sequence.png")
    transforms.append({"output": "assets/flow/reference-snapshots.gif", "source": reference.relative_to(root).as_posix(),
                       "task": "reference simulation, not model inference", "frames_zero_based": indices.tolist(),
                       "physical_time_available": False, "fields": ["sqrt(u^2+v^2)"],
                       "solid_policy": "mask < 0.5, excluded from color limits", "extent": [4,20,6,10],
                       "speed_range": [0,speed_max],
                       "time_policy": "four source snapshots; no interpolation; display timing is illustrative"})

    # Evidence exports are allowlisted to avoid copying machine paths or operational logs.
    car_manifest = read_json(source(crash / "gallery_manifest.json"))

    bumper_metrics = read_json(source(bumper / "stage2_summary.json"))
    bumper_evidence = {k: bumper_metrics[k] for k in ["stage", "task", "case_ids", "case_count", "metric_frame_scope",
                        "metric_reduction", "checkpoint_sha256", "checkpoint_epoch_display", "length_unit", "time_unit"]}
    bumper_evidence["cases"] = [{"case_id": c["case_id"], "shape": c["shape"], "future_metrics": c["future_metrics"]}
                                for c in bumper_metrics["cases"]]
    bumper_evidence["summary"] = {
        "case_mean_vector_rmse": float(np.mean([c["future_metrics"]["vector_rmse"] for c in bumper_metrics["cases"]])),
        "case_mean_displacement_magnitude_r2": float(np.mean([c["future_metrics"]["magnitude_r2_displacement"] for c in bumper_metrics["cases"]])),
        "case_mean_relative_l2_position": float(np.mean([c["future_metrics"]["mean_rel_l2_position"] for c in bumper_metrics["cases"]])),
    }
    write_json(RESULTS / "bumper-stage2.json", bumper_evidence)
    copied(bumper / "r2_per_case_frame.csv", RESULTS / "bumper-per-frame.csv")

    f95 = read_json(source(flow / "stage1_best095_test_all_20261105/metrics.json"))
    keys = ["schema", "checkpoint_sha256", "checkpoint_epoch", "split", "case_count", "case_ids", "channels",
            "reconstruction_scope", "one_step_scope", "reconstruction_inputs", "one_step_inputs", "autoregressive_rollout",
            "relative_error_definition", "mse_definition", "zero_denominator_policy", "original_units", "overall"]
    write_json(RESULTS / "flow-epoch095.json", {k: f95[k] for k in keys})
    f71 = read_json(source(flow / "test_all_stage1_20261029/metrics_summary.json"))
    write_json(RESULTS / "flow-epoch071.json", {k:f71[k] for k in ["schema", "scope", "model_task", "geometry_only_prediction",
                    "stage", "case_count", "checkpoint_epoch", "checkpoint_sha256", "frame_index_zero_based", "case_weighting", "overall"]})
    write_json(RESULTS / "flow-displayed-case.json", {k:sample_meta[k] for k in ["task", "checkpoint_sha256", "checkpoint_epoch",
                "case_id", "split", "Re", "frame_index_zero_based", "time_units", "field_units", "inputs_to_reconstruction", "metrics"]})

    # Compact numeric archive for the case documentation.
    report = {
        "generated_date": "2026-11-06", "car_validation_cases": car_manifest["case_count"],
        "bumper_validation_cases": bumper_evidence["case_count"], "bumper": bumper_evidence["summary"],
        "flow_test_cases": f95["case_count"], "flow_epoch095_reconstruction": f95["overall"]["reconstruction"]["relative_l2_original"],
        "flow_epoch095_one_step": f95["overall"]["one_step"]["relative_l2_original"],
    }
    write_json(RESULTS / "summary.json", report)
    outputs = []
    for directory in [ASSETS, RESULTS]:
        for p in sorted(directory.rglob("*")):
            if p.is_file() and p.name != "provenance.json":
                item = {"path": p.relative_to(REPO).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)}
                if p.suffix in {".png", ".gif"}:
                    with Image.open(p) as pic:
                        item.update({"width": pic.width, "height": pic.height, "frames": getattr(pic, "n_frames", 1)})
                outputs.append(item)
    write_json(RESULTS / "provenance.json", {"source_root": "User-provided local research folder (not distributed)",
        "build_script": "scripts/build_showcase.py", "sources": list(sources.values()), "transformations": transforms, "outputs": outputs})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Built {len(outputs)} assets/evidence files. Total {sum(o['bytes'] for o in outputs)/1024**2:.2f} MiB")


if __name__ == "__main__":
    main()
