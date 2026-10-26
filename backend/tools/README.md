# backend/tools

离线只读工具。**不依赖数据库、FastAPI 运行时或 `app.*`**，可在标注现场直接运行。

## eval_keypoints.py — 关键点精度评估

比较两份关键点，输出逐关节误差与一致性指标。两种用法：

| 用法 | reference | candidate | 回答的问题 |
|---|---|---|---|
| 人工 vs 人工 | 主标注 | 第二标注员盲标 | 人工上限有多高（重测一致性） |
| 模型 vs 人工 | 人工标注 | 模型输出 | 模型离人工上限还差多远 |

### 命令

```bash
cd backend

# 自比对（应全部为 0 误差、ICC=1）
python tools/eval_keypoints.py \
  --reference tests/fixtures/kinematics_golden_v1/source/annotations.xml \
  --candidate tests/fixtures/kinematics_golden_v1/source/annotations.xml \
  --out /tmp/self_report.json

# 两位标注员对比 + markdown 表 + 固化基线
python tools/eval_keypoints.py \
  --reference annotator_a.xml \
  --candidate annotator_b.xml \
  --format cvat \
  --out reports/accuracy_report.json \
  --md-out reports/accuracy_report.md \
  --baseline-out reports/accuracy_baseline.json \
  --reason add-keypoint-accuracy-benchmark
```

### 指标口径

| 指标 | 定义 | 说明 |
|---|---|---|
| `rmse_px` | 逐帧欧氏距离的均方根 | 原始像素，仅同分辨率可比 |
| `rmse_norm` | `rmse_px / 参考体长` | 跨分辨率、跨摄距可比 |
| `pck["0.02"]` 等 | 距离 ≤ 阈值 × 参考体长 的占比 | 阈值 0.02 / 0.05 / 0.10 |
| `oks` | COCO17 sigmas 加权相似度 | 面积取参考关键点包围盒，退化时回退 `(0.5×体长)²` |
| `icc` | ICC(2,1)，帧为 subject、标注员为 rater | 取 x/y 较小值；帧间无变化时为 `null` |

参考体长 = 双肩中点 → 双踝中点距离的**中位数**，与生产 `compute_reference_body_length()` 同口径（`tests/test_keypoint_metrics.py::test_reference_body_length_parity_with_production` 对拍，差 ≤0.01 px）。

### 边界与已知限制

- **只取交集帧**，不插值、不补帧；`pairing.dropped` 会明确记录。
- **不猜测缺失关节**：跨 schema 只评估公共子集，其余进 `skipped_joints`。
- **配对键用图像基名**（`online_06_..._t002.004`），不是纯帧号。多 clip 合并时多个 clip 都从 frame 0 开始，按帧号会静默错配——实测现有素材 119 帧只有 111 个不同帧号，8 个跨 clip 重复。
- CVAT 缺 `name` 会直接报错；COCO 无 `file_name` 回退 `image_id`；归一化 JSON 可用 `frame_key`。
- 两侧键模式不一致 → `key_mode_mismatch`；无共同键 → `frame_space_mismatch`，均不猜对齐方式。
- **基线不自动覆盖**：已存在的 `accuracy_baseline.json` 必须 `--force --reason` 才能更新，理由写入 `approval`。
- OKS 的包围盒会随姿态变化，跨视频比较需谨慎；ICC 受相邻帧自相关影响，只作一致性参考。

### 退出码

| 码 | 含义 |
|---:|---|
| 0 | 成功 |
| 1 | 输入不可解析、无共同帧、参考尺度不可用、基线冲突等（stderr 给出 `code: message`） |
| 2 | 命令行参数错误（argparse） |
