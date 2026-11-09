# 方法、素材生成与仓库结构

[返回主页](../README.md)

## 研究方法概览

![研究流程](../assets/branding/workflow.svg)

结构案例以几何、设计参数和已知初始条件为输入，研究空间编码、潜空间演化和全场解码。Flow 案例研究复杂流体域上的多尺度空间表示，并展示时序预测。实际模型输入与评估范围以各案例说明为准：

- [Car Crash](car-crash.md)：条件驱动的白车身未来位移场。
- [Bumper](bumper.md)：已知初始网格与静态工况下的整段位置轨迹。
- [Flow](flow.md)：重建、预测与原始仿真数据。

## 仓库结构

```text
TPLD-Surrogates/
├── README.md                  # 中文主页
├── README.en.md               # 英文主页
├── assets/
│   ├── branding/              # 方法示意图与品牌素材
│   ├── car-crash/             # GIF、完整对比图
│   ├── bumper/                # GIF、完整对比图、R²曲线
│   └── flow/                  # 预测/重建图集与历史素材
├── docs/                      # 案例、评估口径与方法
├── results/                   # 指标摘要、逐帧表、素材来源
└── scripts/                   # 素材生成与完整性检查
```

## 重新生成展示素材

阅读 GitHub 页面不需要安装依赖。重新生成素材需要本地已有的研究导出目录：

```text
SOURCE_ROOT/
├── 100_Car_Crash/Car_Crash_1026/
├── 131_bumper/Bumper_Visualization/
└── Flow/analysis/
```

在仓库目录执行：

```powershell
python -m pip install -r requirements-showcase.txt
python scripts/build_showcase.py --source-root "D:/research"
python scripts/verify_showcase.py
```

将示例路径替换为实际研究目录。脚本只读取研究目录，并写入本仓库的 `assets/` 和 `results/`，不执行训练或模型推理。

结构动图从原图裁取首个视角的预测、真实值与误差三列，保留色标。全部保存帧按时间顺序生成 GIF，无时间插值。完整 PNG 保留原始字节，用于科学读图。

早期归档的 Flow 原始仿真动图由已有 NPZ 中四个真实快照生成，共用固定速度色标。当前主页采用下文所述的 100 帧模型对比图集。每张素材附任务类型，便于单独分享时保留上下文。

`results/provenance.json` 记录源文件与发布资产的哈希、转换方式及时间政策。当前脚本生成与检查展示包；不提供完整模型训练的可复现实验环境。

## 流场多工况动图

本次图集使用 `scripts/export_flow_gallery.py` 在原研究环境中读取冻结检查点与预处理数据，执行推理并导出仿真、重建和预测场。它不会启动训练或修改模型权重。

在配置好原研究环境和相应路径后执行：

```powershell
python scripts/export_flow_gallery.py --project RESEARCH_PROJECT --checkpoint FROZEN_CHECKPOINT --output PRIVATE_EXPORTS --device cuda:1
python scripts/build_flow_gallery.py --exports PRIVATE_EXPORTS
python scripts/verify_showcase.py
```

导出文件仅作为离线素材输入，不提交到 GitHub。公开仓库保存 GIF、PNG、案例文档和 `results/flow-gallery.json` 中的来源记录。八个测试工况各生成 100 帧预测和重建动画，使用最后 100 个连续保存帧，每帧 50 ms，共用全图集固定横向速度色标。静态高清图包含 u / v / p 与误差。

若先运行原有 `build_showcase.py` 更新结构案例或历史素材，应随后运行 `build_flow_gallery.py`，以刷新图集及统一素材校验清单。
