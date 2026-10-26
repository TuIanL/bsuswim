## Context

系统已有完整的二维运动学链路，但**没有任何"与真值比较"的度量**：`PCK` / `OKS` / `RMSE` / `RMSD` / `ICC` 在 `backend/` 全部 `.py` 中零实现，35 个测试文件全是契约测试。

现有可复用资产：

- `backend/tests/fixtures/kinematics_golden_v1/source/annotations.xml`：104 帧真实 CVAT 标注，COCO17，一条真实侧视片段。
- `fixture_manifest.json`：FPS、分辨率、帧映射口径。
- 生产侧已有参考尺度定义 `compute_reference_body_length()`（shoulder_mid→ankle_mid 中位数，实测 1522.6 px、CV 4.0%）。

约束：

- 工具只读，绝不修改标注、指标或生产数据。
- 不能依赖数据库或 FastAPI 运行时，否则无法在标注现场/离线环境使用。
- 度量必须可复现、可版本化，否则跨时间比较无意义。

## Goals / Non-Goals

**Goals**

1. 给定两份关键点，给出逐关节误差与整体一致性指标，结果写入带 schema 版本的 JSON。
2. 度量口径与生产指标一致（同一参考尺度定义），避免"评估用的尺子和生产用的尺子不一样"。
3. 支持"人工 vs 人工"（建立人工上限）与"模型 vs 人工"（衡量模型差距）两种用法，同一份代码。
4. 输出人可读表，能直接进答辩材料。

**Non-Goals**

1. 不做模型推理、不训练、不接入 YOLO/RTMPose。
2. 不改进任何指标或滤波；本工具只测量。
3. 不做逐帧可视化叠加图（后续可另开）。
4. 不改生产代码、不加 CI job、不改现有门禁。

## Decisions

### Decision 1: 归一化基准用"参考体长"，与生产同口径

- **选择**：`reference_body_length = median(shoulder_mid→ankle_mid)`，取自 reference 一侧全部可用帧。
- **理由**：生产指标 `compute_reference_body_length()` 用的就是它；评估用同一把尺子，误差才能直接解释成"对指标的影响"。
- **备选与否决**：躯干长度（更稳但基数小，会把误差放大 2 倍，读数不直观）；画面宽度（随摄距变化，跨视频不可比）。
- **实现约束**：工具不 import `app.*`（保持离线可用），但在 tools 内实现同口径函数，并用对拍测试锁死两边一致。

### Decision 2: PCK 阈值以体长为单位，取 0.02 / 0.05 / 0.10

- **理由**：1522.6 px 体长下，0.02 ≈ 30 px，接近 4K 画面里腕关节的可辨精度；0.05 ≈ 76 px 是"肉眼明显偏差"的边界；0.10 用于宽容口径对比。
- **备选与否决**：像素阈值（跨分辨率不可比）、头部尺寸归一化（游泳侧视下水花常遮挡头部，尺度不稳）。
- **注意**：PCK 只统计两侧都可见的关节；`visible=false` 的帧不参与该关节的 PCK 分母。

### Decision 3: OKS 用 COCO17 sigmas，尺度用 reference 关键点包围盒

- 标准 OKS 需要目标面积（通常取检测框面积）。本工具只吃关键点，因此：
  - `area = (max_x - min_x) * (max_y - min_y)`，基于 reference 全部可见关节；
  - 若 `area` 退化为 0 或过小，回退为 `(0.5 × reference_body_length)^2`，并在报告 `params.area_source` 里写明用了哪一种。
- **理由**：不引入对检测框的依赖，同时保留"尺度归一化"这一 OKS 的核心语义。
- **风险披露**：包围盒会随姿态变化（伸臂时变大），因此 OKS 在同一视频内可比、跨视频需谨慎。报告 `caveats` 必须写明。

### Decision 4: ICC 以"帧"为 subject、"标注员"为 rater，x 与 y 分别算

- **选择**：对每个关节，构造 `n_frames × 2_raters` 矩阵，分别对 x、y 计算 ICC(2,1)（two-way random effects, absolute agreement, single measure），报告 `min(icc_x, icc_y)`。
- **理由**：ICC 衡量的是"评分者一致性"，必须有 subject × rater 结构；把误差均值当评分是误用。取 min 是保守口径。
- **备选与否决**：对每帧欧氏距离算 ICC（无 rater 维度，数学上不成立）；只报 Pearson r（对系统偏移不敏感，标定偏了也看不出来）。
- **限制**：相邻帧高度自相关会让 ICC 虚高，报告必须写明"ICC 仅作一致性参考，不作为显著性结论"。

### Decision 5: 帧配对只取交集，且以图像基名为主键

- **配对键**：默认用图像基名（`Path(file_name).stem`），因为同一份导出里可能混有多个 clip——实测现有素材 119 个标注帧只有 111 个不同帧号，**8 个帧号跨 clip 重复**（多个 clip 都从 frame 0 开始）。按帧号配对会把不同泳者的帧当成同一帧比较。
- **回退**：COCO 无 `file_name` 时用 `image_id`；归一化 JSON 无 `frame_key` 时用 `annotation_frame` 字符串。
- **拒绝策略**：两侧 `key_mode` 不一致（一侧图像名、一侧帧号）→ `key_mode_mismatch`；两侧无任何共同键 → `frame_space_mismatch`。绝不猜对齐方式。
- **只取交集**：只评估两侧都存在的帧；丢弃数写入 `report.pairing`。
- **理由**：评估工具引入插值等于自己造数据，会把"模型在缺失帧上不输出"这种真实缺陷洗掉。
- **备选与否决**：按帧号配对（多 clip 会静默错配）；按序号配对（导出顺序变化即失效）。

### Decision 6: 跨 schema 按关节名规范化映射，缺映射即跳过并记录

- 规范化规则：小写、`_` 与空格统一为 `-`（`left_shoulder` / `left-shoulder` / `Left Shoulder` → `left-shoulder`）。
- COCO17 与 halpe26 的公共子集参与评估；只在单侧存在的关节进入 `skipped_joints`，**MUST NOT 猜测或补点**。
- **理由**：宁可少算几个关节，也不让评估结果混入构造数据。

### Decision 7: 输出 `accuracy-report.v1`，字段固定

```json
{
  "schema_version": "accuracy-report.v1",
  "generated_at": "2026-10-25T12:00:00Z",
  "inputs": {"reference": {"path": "...", "sha256": "...", "frames": 104},
             "candidate": {"path": "...", "sha256": "...", "frames": 104}},
  "pairing": {"frame_space": "annotation", "paired_frames": 104, "dropped": 0},
  "params": {"reference_body_length_px": 1522.6, "pck_thresholds": [0.02, 0.05, 0.10],
             "oks_sigmas": "coco17.v1", "area_source": "keypoint_bbox"},
  "per_joint": [{"joint": "left-wrist", "n": 104, "rmse_px": 41.2, "rmse_norm": 0.027,
                 "pck": {"0.02": 0.62, "0.05": 0.94, "0.10": 1.0},
                 "oks": 0.87, "icc_x": 0.81, "icc_y": 0.78, "rank": 1}],
  "aggregate": {"joints_evaluated": 17, "rmse_norm_mean": 0.018,
                "rmse_norm_median": 0.014, "worst_three": ["left-wrist", "right-ankle", "left-ankle"]},
  "skipped_joints": [],
  "caveats": ["ICC 受相邻帧自相关影响，仅作一致性参考"]
}
```

- **理由**：字段固定 + schema 版本，才能让 `accuracy_baseline.json` 在几个月后仍可比较；`rank` 让"最难关节"一眼可见。

### Decision 8: 基线文件不自动覆盖

- `--baseline-out` 仅在该路径不存在时写入；已存在时必须显式 `--force --reason "<change-id>"`，且 reason 写进文件的 `approval` 字段。
- **理由**：与既有 golden baseline 治理保持一致，防止"跑一次就把新数字当标准答案"。

### Decision 9: 纯函数与 I/O 分离，便于测试与复用

- `keypoint_metrics.py`：无 I/O 的纯函数（输入 `dict[frame, dict[joint, tuple]]`）。
- `keypoint_sources.py`：三种读取器 + 关节名规范化。
- `eval_keypoints.py`：CLI、参数校验、报告写出。
- **理由**：指标可以用"已知答案"用例锁死（例如人为平移 10px，RMSE 必须等于 10），不需要真实标注。

## Risks / Trade-offs

- **[参考体长口径漂移]** tools 内重写一份参考体长计算，可能日后与生产不一致 → 用对拍测试：同一份标注，tools 与 `compute_reference_body_length()` 结果差 ≤0.01 px，超出即失败。
- **[OKS 包围盒随姿态变化]** 伸臂帧面积大、抱水帧面积小 → 报告 `area_source` 与 `caveats` 明示，跨视频比较需谨慎；必要时后续改为固定标定尺度。
- **[样本量小]** 30–104 帧不足以支撑统计显著性 → 报告只给点估计与 n，不做显著性断言；`caveats` 写明。
- **[ICC 自相关]** 相邻帧高度相关导致 ICC 偏高 → 报告标注限制，建议 P0-2 复标时按动作周期抽样而非连续帧。
- **[工具与生产脱节]** tools 不被 CI 覆盖时容易腐烂 → 新测试进普通 pytest（`backend/tests/`），随现有门禁一起跑。

## Migration Plan

新增独立工具，无数据迁移、无部署动作。合并后即可离线使用：

```bash
cd swim/backend
python tools/eval_keypoints.py \
  --reference tests/fixtures/kinematics_golden_v1/source/annotations.xml \
  --candidate /path/to/second_annotator.xml \
  --format cvat --out /tmp/accuracy_report.json
```

回滚：删除 `backend/tools/` 与两个测试文件即可，无副作用。

## Open Questions

- 是否需要"仅上肢 6 点"的子集模式（P2 若先做上肢，评估应能对齐）→ 倾向后续加 `--joints` 过滤，本 Change 不做。
- 是否需要逐帧误差的可视化叠加图 → 后续按需另开，避免本 Change 膨胀。
