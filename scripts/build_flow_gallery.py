"""Render scientific comparison GIFs from actual exported model arrays."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets/flow/gallery"
CASES = [
    ("harmonics-92-Re-272", "圆钝形", "圆钝物体后的交替尾迹"),
    ("harmonics-92-Re-411", "圆钝形", "较高 Re 下的尾迹间距与横向扩展"),
    ("harmonics-17-Re-166", "多瓣形", "多瓣边界后的近尾迹发展"),
    ("harmonics-17-Re-974", "多瓣形", "偏转尾迹与不规则横向速度结构"),
    ("nurbs-62-Re-179", "细长形", "倾斜细长物体后的尾迹"),
    ("nurbs-62-Re-979", "细长形", "较大尺度的尾迹摆动与疏密变化"),
    ("nurbs-87-Re-311", "不对称形", "不对称边界引起的偏转与交替响应"),
    ("nurbs-87-Re-874", "不对称形", "丰富的尾迹速度结构与横向变化"),
]
NAVY = "#102a38"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def exported_file(folder, slug, suffix):
    return folder / (slug.replace("-Re-", "-Re_") + suffix)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def font(size, bold=False):
    for p in [Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
              Path(matplotlib.get_data_path()) / "fonts/ttf" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise FileNotFoundError("TrueType font required")


def scientific_frame(true, model, mask, meta, index, task, limit):
    im = Image.new("RGB", (1100, 748), "#ffffff")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1100, 86), fill=NAVY)
    d.rectangle((0, 0, 7, 86), fill="#53d9c6")
    d.text((28, 13), meta["case_id"], font=font(28, True), fill="white")
    d.text((29, 52), f'Cross-stream velocity v  |  saved frame {meta["frame_indices"][index]+1}/242  |  {index+1:03d}/100',
           font=font(19), fill="#c5dee6")
    cmap = plt.get_cmap("RdBu_r")
    for field, y, title in [(true, 132, "SIMULATION"),
                            (model, 424, "ONE-STEP PREDICTION" if task == "prediction" else "AE RECONSTRUCTION")]:
        d.text((48, y-33), title, font=font(20, True), fill=NAVY)
        rgb = np.asarray(cmap(np.clip((field+limit)/(2*limit), 0, 1), bytes=True)[..., :3]).copy()
        rgb[~mask] = (45, 58, 68)
        panel = Image.fromarray(rgb[::-1]).resize((960, 240), Image.Resampling.NEAREST)
        im.paste(panel, (48, y))
        d.rectangle((48, y, 1008, y+240), outline="#a9bac5", width=1)
        d.text((18, y-4), "10", font=font(13), fill="#536b79")
        d.text((23, y+224), "6", font=font(13), fill="#536b79")
        for x, value in [(48, "4"), (288, "8"), (528, "12"), (768, "16"), (992, "20")]:
            d.text((x, y+243), value, font=font(13), fill="#536b79")
    bar = np.asarray(cmap(np.linspace(1, 0, 532), bytes=True)[..., :3])[:, None, :]
    im.paste(Image.fromarray(np.repeat(bar, 17, axis=1)), (1032, 132))
    for y, v in [(128, limit), (388, 0), (651, -limit)]:
        d.text((1053, y), f"{v:.1f}", font=font(14), fill=NAVY)
    d.text((1032, 102), "v", font=font(17, True), fill=NAVY)
    d.line((28, 699, 1072, 699), fill="#d7e4eb", width=1)
    note = "Inputs: geometry, Re + two true historical fields" if task == "prediction" else "Inputs: geometry, Re + true field at the displayed time"
    d.text((29, 711), note, font=font(17), fill="#536b79")
    return im


def save_gif(frames, path):
    # Fixed palette preserves a stable shared scientific color scale across time.
    # Web GIFs use a compact display size; PNGs keep the larger render.
    frames = [f.resize((800,544), Image.Resampling.LANCZOS) for f in frames]
    sample = Image.new("RGB", (275, 187*20), "white")
    for j, i in enumerate(np.linspace(0, 99, 20, dtype=int)):
        sample.paste(frames[i].resize((275,187)), (0,j*187))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=50,
                    loop=0, disposal=2, optimize=False)
    with Image.open(path) as im:
        assert im.n_frames == 100
        assert all(f.info.get("duration") == 50 for f in ImageSequence.Iterator(im))


def full_comparison(truth, model, mask, meta, task, path):
    fig, axes = plt.subplots(3, 3, figsize=(18, 7.8), layout="constrained")
    label = "One-step prediction" if task == "prediction" else "AE reconstruction"
    for channel, name in enumerate(["u", "v", "p"]):
        a, b = truth[-1,...,channel], model[-1,...,channel]
        lower = float(min(a[mask].min(), b[mask].min()))
        upper = float(max(a[mask].max(), b[mask].max()))
        error = np.abs(b-a)
        for col, values, title, cmap, lo, hi in [
            (0,a,"Simulation","RdBu_r",lower,upper),
            (1,b,label,"RdBu_r",lower,upper),
            (2,error,"Absolute error","magma",0,float(error[mask].max()))]:
            ax=axes[channel,col]
            palette=plt.get_cmap(cmap).copy();palette.set_bad("#2d3a44")
            pic=ax.imshow(np.ma.array(values,mask=~mask),origin="lower",extent=(4,20,6,10),
                          cmap=palette,vmin=lo,vmax=max(hi,lo+1e-12),interpolation="nearest",aspect="equal")
            ax.set_title(f"{name} | {title}",loc="left",fontsize=12)
            ax.set_xlabel("x");ax.set_ylabel("y")
            fig.colorbar(pic,ax=ax,shrink=.70,pad=.025)
    note="Two true preceding fields enter each prediction" if task=="prediction" else "Current true field enters reconstruction"
    fig.suptitle(meta["case_id"]+" | saved frame 242 | "+note+"\nOriginal stored field units; matched color scales for simulation and model",fontsize=15)
    fig.savefig(path,dpi=120);plt.close(fig)


def case_doc(slug, meta, shape, feature):
    return f'''# {shape} · {meta["case_id"]}

[主页](../../README.md) · [绕流预测图集](../flow-prediction.md) · [流场重建图集](../flow-reconstruction.md)

该工况来自固定测试集。关注：{feature}。几何与 Re 是共同的静态条件；下列两个任务的流场输入不同。

## 仿真与单步预测

每次预测输入前两帧真实流场及实际查询间隔。动画连续展示 100 个时刻的单步预测，不是 100 步自由滚动。

![仿真与单步预测的100帧对比](../../assets/flow/gallery/{slug}/prediction.gif)

[打开末帧 u / v / p、预测与误差高清图](../../assets/flow/gallery/{slug}/prediction-fields.png)

## 仿真与空间重建

当前时刻的真实场进入编码器，图中对比仿真场与同一时刻的自编码器重建。

![仿真与空间重建的100帧对比](../../assets/flow/gallery/{slug}/reconstruction.gif)

[打开末帧 u / v / p、重建与误差高清图](../../assets/flow/gallery/{slug}/reconstruction-fields.png)

两组动画都展示原始保存序号 143–242 的 100 个连续帧，每帧 50 ms（20 fps）；播放时间仅用于网页演示。动画显示横向速度 v，所有工况和时刻共用固定色标，深灰色为固体。原始网格 1024 × 256，网页素材从每个方向每隔一个节点取样为 512 × 128，不插入时间中间帧。模型来源与导出记录见 [素材记录](../../results/flow-gallery.json)。
'''


def gallery_doc(task, cases):
    prediction=task=="prediction"
    heading="绕流演化：仿真与单步预测" if prediction else "流场重建：不同形状与雷诺数"
    intro=("每次预测使用几何、Re、前两帧真实流场和实际时间间隔。这里连续展示 100 个单步预测结果，未进行长期自由滚动。" if prediction else
           "每个时刻将真实流场输入自编码器，比较仿真场与重建场，观察不同几何和 Re 下的空间表示能力。")
    other="flow-reconstruction.md" if prediction else "flow-prediction.md"
    text=f'''# {heading}

[返回主页](../README.md) · [Flow 研究说明](flow.md) · [另一组对比图集]({other})

{intro}

四类几何、八个测试工况，每段 GIF 都包含 **100 个连续保存帧，以 20 fps 播放**。下图展示横向速度 v，以便观察交替尾迹、偏转与横向变化。所有动画共用同一固定色标，仿真与模型结果严格对齐；点击动图可进入该工况的预测、重建与 u / v / p 高清对比。

案例按几何形状、Re 覆盖和仿真流场特征选择，未按模型误差筛选。形状名称用于帮助浏览；不同 Re 的流动变化应结合具体几何阅读。

'''
    for i in range(0,len(cases),2):
        a,b=cases[i:i+2]
        text+=f'## {a["shape"]} · {a["case_id"].rsplit("/",1)[0]}\n\n'
        text+='<table>\n<tr>' + ''.join(f'<th width="50%">Re = {c["Re"]}</th>' for c in [a,b])+'</tr>\n<tr>'
        for c in [a,b]:
            text+=f'<td><a href="flow-cases/{c["slug"]}.md"><img src="../assets/flow/gallery/{c["slug"]}/{task}.gif" width="100%" alt="{c["case_id"]} 仿真与模型100帧对比" /></a></td>'
        text+='</tr>\n<tr>'+''.join(f'<td>{c["feature"]}<br/><a href="flow-cases/{c["slug"]}.md">查看该工况完整对比 →</a></td>' for c in [a,b])+'</tr>\n</table>\n\n'
    text+='原始保存序号为 143–242（零基索引 142–241），未进行时间插值。每段循环结束后返回第一帧。原始网格 1024 × 256；导出时两个方向均每隔一个节点取样至 512 × 128。色标为数据原始存储尺度，时间不换算为未经核实的物理秒数。详细来源见 [导出记录](../results/flow-gallery.json)。\n'
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exports",type=Path,required=True)
    args=p.parse_args()
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ROOT/"docs/flow-cases").mkdir(exist_ok=True)
    limit=0.
    for slug,_,_ in CASES:
        with np.load(exported_file(args.exports,slug,".npz"),allow_pickle=False) as z:
            mask=z["fluid_mask"]
            for key in ["truth","prediction","reconstruction"]:
                limit=max(limit,float(np.abs(z[key][...,1][:,mask]).max()))
    limit=float(np.ceil(limit*10)/10)
    cases=[]
    for slug,shape,feature in CASES:
        src=exported_file(args.exports,slug,".npz")
        meta=json.loads(exported_file(args.exports,slug,".json").read_text())
        assert digest(src)==meta["array_sha256"]
        dest=ASSETS/slug;dest.mkdir(exist_ok=True)
        with np.load(src,allow_pickle=False) as z:
            mask=z["fluid_mask"];truth=z["truth"]
            assert len(truth)==100 and np.all(np.diff(z["frame_indices"])==1)
            assert np.array_equal(z["history_raw_triplets"][:,2],z["frame_indices"])
            assert np.all(np.diff(z["history_raw_triplets"],axis=1)==1)
            metrics={}
            for task in ["prediction","reconstruction"]:
                values=z[task]
                assert values.shape==truth.shape and np.isfinite(values).all()
                frames=[scientific_frame(truth[i,...,1],values[i,...,1],mask,meta,i,task,limit) for i in range(100)]
                save_gif(frames,dest/(task+".gif"))
                frames[-1].save(dest/(task+"-preview.png"),optimize=True)
                full_comparison(truth,values,mask,meta,task,dest/(task+"-fields.png"))
                delta=(values[:,mask]-truth[:,mask]).astype(np.float64)
                metrics[task]=np.sqrt((delta**2).sum(axis=(0,1))/(truth[:,mask].astype(np.float64)**2).sum(axis=(0,1))).tolist()
            meta.update(slug=slug,shape=shape,feature=feature,
                        visualization_relative_l2=metrics,metric_scope="100 displayed frames at exported fluid nodes; not full test-set metrics")
        cases.append(meta)
        (ROOT/"docs/flow-cases"/(slug+".md")).write_text(case_doc(slug,meta,shape,feature),encoding="utf-8",newline="\n")
        print(json.dumps({"case":meta["case_id"],"gif_mib":[round((dest/(t+".gif")).stat().st_size/1048576,2) for t in ["prediction","reconstruction"]]}),flush=True)
    report=dict(schema="tpld_flow_gallery_v1",frames_per_gif=100,duration_ms_per_frame=50,
                gif_display_size=[800,544],gif_color_policy="Shared 256-color palette across each animation; display resized with Lanczos; larger PNG previews retained",
                fps=20,field="v",color_range=[-limit,limit],case_selection="Geometry, Re coverage and reference-flow patterns; no error-based selection",cases=cases)
    write_json(ROOT/"results/flow-gallery.json",report)
    for task in ["prediction","reconstruction"]:
        (ROOT/"docs"/("flow-"+task+".md")).write_text(gallery_doc(task,cases),encoding="utf-8",newline="\n")
    provenance=json.loads((ROOT/"results/provenance.json").read_text())
    provenance["flow_gallery"]={"record":"results/flow-gallery.json","build_script":"scripts/build_flow_gallery.py", "export_script":"scripts/export_flow_gallery.py"}
    outputs=[]
    for directory in [ROOT/"assets",ROOT/"results"]:
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name=="provenance.json":continue
            entry=dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=digest(path))
            if path.suffix in [".gif",".png"]:
                with Image.open(path) as im:entry.update(width=im.width,height=im.height,frames=getattr(im,"n_frames",1))
            outputs.append(entry)
    provenance["outputs"]=outputs
    write_json(ROOT/"results/provenance.json",provenance)


if __name__=="__main__":main()
