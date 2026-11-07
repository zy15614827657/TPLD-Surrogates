"""Check the distributable research showcase without requiring source datasets."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]


def main():
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)

    paths = [p for p in ROOT.rglob("*") if p.is_file() and not any(x in {".git", ".local", ".venv", "__pycache__"} for x in p.relative_to(ROOT).parts)]
    provenance = json.loads((ROOT / "results/provenance.json").read_text(encoding="utf-8"))
    for entry in provenance["outputs"]:
        path = ROOT / entry["path"]
        check(path.is_file(), f"Missing asset: {entry['path']}")
        if path.is_file():
            check(hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"Asset hash mismatch: {entry['path']}")

    links_checked = 0
    for path in paths:
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            refs = re.findall(r"\[[^\]]*\]\(([^)]+)\)", content) + re.findall(r'(?:src|href)="([^"]+)"', content)
            for ref in refs:
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                check(target.is_relative_to(ROOT), f"Link leaves repository: {path.name} -> {ref}")
                check(target.exists(), f"Broken link: {path.relative_to(ROOT)} -> {ref}")
                if url.fragment and target.is_file() and target.suffix == ".md":
                    check(f'id="{url.fragment}"' in target.read_text(encoding="utf-8"), f"Missing explicit anchor: {ref}")
                links_checked += 1
        elif path.suffix == ".svg":
            ET.parse(path)
        elif path.suffix in {".png", ".gif"}:
            with Image.open(path) as im:
                im.verify()
        check(path.stat().st_size < 50 * 1024**2, f"File exceeds 50 MiB: {path.name}")
        if path.suffix in {".json", ".csv", ".md"}:
            text = path.read_text(encoding="utf-8-sig")
            check(not re.search(r"\b[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]|/data/ZhangYuan/|gh[pousr]_[A-Za-z0-9]{20,}", text), f"Machine path or token-like text in publication: {path.name}")

    gif_details = []
    gif_specs = [("assets/car-crash/prediction.gif", 13), ("assets/bumper/prediction.gif", 11), ("assets/flow/reference-snapshots.gif", 4)]
    gallery_path = ROOT / "results/flow-gallery.json"
    if gallery_path.exists():
        gallery = json.loads(gallery_path.read_text(encoding="utf-8"))
        for case in gallery["cases"]:
            indices = case["frame_indices"]
            check(len(indices) == 100 and all(b-a == 1 for a,b in zip(indices,indices[1:])), f"Nonconsecutive flow frames: {case['case_id']}")
            check(case["split"] == "test" and not case["autoregressive_rollout"], f"Invalid gallery task metadata: {case['case_id']}")
            for task in ["prediction", "reconstruction"]:
                gif_specs.append((f"assets/flow/gallery/{case['slug']}/{task}.gif", 100))
    for rel, expected in gif_specs:
        with Image.open(ROOT / rel) as im:
            check(im.n_frames == expected, f"Unexpected GIF frame count: {rel}")
            check(im.info.get("loop") == 0, f"GIF does not loop: {rel}")
            hashes = set()
            for frame in ImageSequence.Iterator(im):
                check(frame.info.get("duration", 0) > 0, f"Missing frame timing: {rel}")
                if expected == 100:
                    check(frame.info.get("duration") == 50, f"Flow GIF is not 20 fps: {rel}")
                hashes.add(hashlib.sha256(frame.convert("RGB").tobytes()).hexdigest())
            check(len(hashes) == expected, f"Duplicate frames in GIF: {rel}")
            gif_details.append({"path": rel, "frames": im.n_frames, "bytes": (ROOT/rel).stat().st_size})

    report = {"passed": not failures, "files": len(paths), "local_links_checked": links_checked,
              "total_mib": round(sum(p.stat().st_size for p in paths)/1024**2, 2), "gifs": gif_details,
              "asset_hashes_checked": len(provenance["outputs"]), "failures": failures}
    (ROOT / ".local").mkdir(exist_ok=True)
    (ROOT / ".local/verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
