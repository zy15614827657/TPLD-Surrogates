"""Export real test-case fields from an existing Flow research checkpoint.

Run in the research environment. This performs inference only. The one-step
prediction receives the two preceding true fields; it never receives its target.
Raw arrays remain outside the public showcase repository.
"""
from __future__ import annotations
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

CASES = [
    "harmonics/92/Re_272", "harmonics/92/Re_411",
    "harmonics/17/Re_166", "harmonics/17/Re_974",
    "nurbs/62/Re_179", "nurbs/62/Re_979",
    "nurbs/87/Re_311", "nurbs/87/Re_874",
]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--device", default="cuda:1")
    p.add_argument("--cases", nargs="+", default=CASES)
    args = p.parse_args()
    sys.path.insert(0, str(args.project.resolve()))
    from fpo.data import FlowDataset
    from fpo.model import FPOModel
    from fpo.train import (autocast, canonical_times, checkpoint_training_config,
        configure_runtime, load_checkpoint, make_one_step_predictor, make_static,
        query_grid, temporal_start_index, validate_query_grid)

    torch.set_num_threads(4)
    device = torch.device(args.device)
    if device.type == "cuda":
        torch.cuda.set_per_process_memory_fraction(.15, device)
    args.output.mkdir(parents=True, exist_ok=True)
    saved = load_checkpoint(args.checkpoint)
    checkpoint_sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    data = FlowDataset(args.project / "prepared")
    assert saved["stage"] == 1
    assert data.identity == saved["data_identity"]
    assert data.normalization == saved["normalization"]
    validate_query_grid(saved, data.manifest)
    cfg = checkpoint_training_config(saved["training_config"])
    cfg["static_cache_entries"] = 1
    model = FPOModel(saved["model_config"], saved["normalization"]).to(device)
    model.load_state_dict(saved["model_state"], strict=True)
    configure_runtime(model, cfg, stage=1)
    predictor = make_one_step_predictor(model, cfg, saved)
    assert predictor is not None
    model.eval().requires_grad_(False)
    predictor.eval().requires_grad_(False)
    times = canonical_times(data, device)
    _, raw_indices = query_grid(data.manifest)
    excluded = {"/".join(c.split("/")[:2]) for key in ("training_case_ids", "validation_case_ids") for c in saved[key]}
    started = time.monotonic()
    for case_id in args.cases:
        slug = case_id.replace("/", "-")
        dest = args.output / (slug + ".npz")
        meta_path = args.output / (slug + ".json")
        if dest.exists() and meta_path.exists():
            old = json.loads(meta_path.read_text())
            assert old["checkpoint_sha256"] == checkpoint_sha
            assert old["array_sha256"] == hashlib.sha256(dest.read_bytes()).hexdigest()
            print(json.dumps({"case": case_id, "state": "already_exported"}), flush=True)
            continue
        row = data._record(case_id)
        assert row["split"] == "test" and row["geometry_group"] not in excluded
        static, fluid = make_static(model, data, row)
        h, w = fluid.shape
        yy, xx = np.mgrid[0:h:2, 0:w:2]
        nodes_cpu = (yy * w + xx).reshape(-1)
        nodes = torch.as_tensor(nodes_cpu, device=device)
        mask = fluid[::2, ::2]
        target_indices = np.arange(int(row["frames"]) - 100, int(row["frames"]))
        assert target_indices[0] - 2 >= temporal_start_index(data, int(row["frames"]), cfg)
        assert np.all(np.diff(raw_indices[target_indices]) == 1)
        history = deque(maxlen=2)
        truth, reconstruction, prediction = [], [], []
        for index in range(int(target_indices[0]) - 2, int(target_indices[-1]) + 1):
            predicted = None
            if len(history) == 2:
                assert [x[0] for x in history] == [index - 2, index - 1]
                with autocast(device, cfg["amp"]):
                    predicted = predictor(history[0][1], history[1][1], static,
                        times[index-1]-times[index-2], times[index]-times[index-1])
            # The current true field is only used by reconstruction and later history.
            fields = data.read_frames(row, [index])
            q = torch.as_tensor(np.ascontiguousarray(data.normalize(fields)), device=device)
            with autocast(device, cfg["amp"]):
                encoded = model.encode(q, static)
            if predicted is not None:
                with autocast(device, cfg["amp"]):
                    values = model.decode(torch.cat([predicted, encoded]), static,
                        node_indices=nodes, node_chunk_size=8192)
                values = data.denormalize(values.float().cpu().numpy()).reshape(2, *mask.shape, 3)
                assert np.isfinite(values).all()
                truth.append(fields[0, ::2, ::2].copy())
                prediction.append(values[0])
                reconstruction.append(values[1])
            history.append((index, encoded))
            if len(truth) and len(truth) % 20 == 0:
                progress = {"state": "exporting", "case": case_id, "frames": len(truth),
                            "elapsed_seconds": round(time.monotonic()-started, 1)}
                write_json(args.output / "progress.json", progress)
                print(json.dumps(progress), flush=True)
        assert len(truth) == len(prediction) == len(reconstruction) == 100
        np.savez_compressed(dest, truth=np.asarray(truth), prediction=np.asarray(prediction),
            reconstruction=np.asarray(reconstruction), fluid_mask=mask,
            frame_indices=raw_indices[target_indices], query_times=times[target_indices].cpu().numpy(),
            history_raw_triplets=np.stack([raw_indices[target_indices-2], raw_indices[target_indices-1], raw_indices[target_indices]], axis=1),
            x=(4+(np.arange(w)+.5)*16/w)[::2], y=(6+(np.arange(h)+.5)*4/h)[::2])
        meta = dict(case_id=case_id, family=row["family"], geometry_id=row["geometry_id"],
            Re=int(row["Re"]), split="test", checkpoint_epoch=int(saved["epoch"])+1,
            checkpoint_sha256=checkpoint_sha, data_identity=data.identity,
            geometry_sha256=row["geometry_sha256"], source_signature=row["source_signature"],
            channels=["u", "v", "p"], frames=100, frame_indices=raw_indices[target_indices].tolist(),
            native_grid=[h,w], export_grid=list(mask.shape),
            spatial_policy="Every second original grid node on each axis; no field interpolation",
            time_policy="Last 100 consecutive saved frames; no temporal interpolation",
            reconstruction_inputs=["geometry", "Re", "true field at current time"],
            prediction_inputs=["geometry", "Re", "two preceding true fields", "actual query intervals"],
            autoregressive_rollout=False, field_units="Original stored units; not verified SI units",
            time_units="Normalized saved-frame coordinate; not physical seconds",
            array_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
            bytes=dest.stat().st_size)
        write_json(meta_path, meta)
        print(json.dumps({"case": case_id, "state": "complete", "bytes": dest.stat().st_size,
                          "elapsed_seconds": round(time.monotonic()-started, 1)}), flush=True)
    write_json(args.output / "progress.json", {"state": "completed", "cases": args.cases,
               "elapsed_seconds": round(time.monotonic()-started, 1)})


if __name__ == "__main__":
    main()
