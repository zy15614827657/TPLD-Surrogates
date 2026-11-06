# 评估口径与结果索引

[返回主页](../README.md)

仓库中的百分比表示相对 L2 误差乘以 100。不同案例的任务、输入、物理量与归约方式不同，因此不将这些数字合并为统一准确率。

| 结果文件 | 检查点与数据范围 | 主要内容 |
| :--- | :--- | :--- |
| [car-crash.json](../results/car-crash.json) | Stage 3，第 5 轮最佳模型；18 个验证工况 | 每工况每帧的节点空间 R²、SSE、SST |
| [car-crash-per-frame.csv](../results/car-crash-per-frame.csv) | 同上 | 原始逐帧表的完整副本 |
| [bumper-stage2.json](../results/bumper-stage2.json) | Stage 2，第 615 轮最佳模型；7 个验证工况 | 每工况未来帧位置与位移指标；工况均值 |
| [bumper-per-frame.csv](../results/bumper-per-frame.csv) | Stage 1 与 Stage 2；按阶段字段区分 | 逐帧位移 R²、SSE、SST、RMSE、MAE |
| [flow-epoch071.json](../results/flow-epoch071.json) | Stage 1，Epoch 71；85 个测试工况的最后保存帧 | 与展示图册同版本的全工况汇总 |
| [flow-displayed-case.json](../results/flow-displayed-case.json) | `nurbs/87/Re_874`，Epoch 71 | 展示工况、输入字段与单帧指标 |
| [flow-epoch095.json](../results/flow-epoch095.json) | Stage 1，Epoch 95；85 个测试工况 | 全帧重建、匹配目标帧重建、单步预测及保持上一帧基线 |
| [summary.json](../results/summary.json) | 对上述文件的数值提取 | 主页所用数值 |

## 阅读结构指标

车辆碰撞的逐帧 R² 是单个时刻在全部节点上的空间分布指标。`t=0` 是已知初始条件，R² 留空；真值方差为零时也留空。所有负 R² 保留。

保险杠主页上的位移幅值 R² 则先在一个工况的全部未来帧与节点上计算，再对工况等权平均。它与 CSV 中逐帧空间 R² 的均值不同。向量误差为 `||P_pred−P_true||=||U_pred−U_true||`，包含方向差异；合位移幅值误差为 `| ||U_pred||−||U_true|| |`，二者不同。

绝对位置相对 L2 的分母是位置，位移相对 L2 的分母是位移，不能互相替代。保险杠使用源长度/时间单位，未擅自换算为 mm/ms。

## 阅读流场指标

Epoch 95 中的相对 L2 按通道计算：

```text
relative L2(case, channel) = sqrt(Σ(pred−truth)² / Σtruth²)
reported relative L2(channel) = mean_over_cases(relative L2(case, channel))
```

求和区域为该任务评估的全部有效时刻与流体像素，固体不参与统计。归约为工况等权，不等于直接把所有工况拼接后的 pooled 指标。

全有效帧重建使用当前真实场；单步预测使用两帧真实历史场。模型没有在此评估中连续使用自己的预测作为后续输入，因此单步误差不能代表长期自由滚动误差。

## 素材与复核

所有发布素材记录在 [provenance.json](../results/provenance.json)，包括源文件的相对路径与 SHA-256、图片裁切范围、动画帧序号及生成后文件校验值。原始研究目录作为离线输入，不随展示仓库分发。

病例图片用于展示研究内容，不代替完整验证/测试分区的统计。本版本不发布尚未核验的加速倍数或跨任务综合性能结论。
