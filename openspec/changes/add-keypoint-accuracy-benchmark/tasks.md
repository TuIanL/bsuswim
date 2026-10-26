## 1. 工具骨架与输入适配

- [x] 1.1 新建 `backend/tools/__init__.py`（空包，便于 `python -m tools.…` 与 pytest 导入）
- [x] 1.2 新建 `backend/tools/keypoint_sources.py`，定义统一内存结构 `dict[int, dict[str, Point]]`，`Point` 含 `x`、`y`、`visible`
- [x] 1.3 实现 CVAT Skeleton XML 读取器（stdlib `ElementTree`，自包含，不 import `app.*`）；用对拍测试与生产 `parse_cvat_xml` 对齐
- [x] 1.4 实现 COCO keypoints JSON 读取器：兼容 `annotations[].keypoints`（扁平数组）与显式点列表两种写法
- [x] 1.5 实现归一化 `keypoint_frames` JSON 读取器：字段为 `frame`/`annotation_frame` 与 `points[]`
- [x] 1.6 实现关节名规范化：小写、`_` 与空格统一为 `-`；输出稳定的 canonical 名称
- [x] 1.7 实现 schema 对齐：按规范化名求交集，单侧关节写入 `skipped_joints` 并附原因，禁止补点
- [x] 1.8 实现参考体长计算（肩中点→踝中点逐帧距离的中位数），与生产 `compute_reference_body_length()` 同口径
- [x] 1.9 配对键策略：CVAT/COCO 用图像基名（`frame_key` / `image_id` 回退），CVAT 缺 `name` 时直接报错而非按序号猜
- [x] 1.10 报告写入 `pairing.key_mode`；两侧键模式不一致时报 `key_mode_mismatch`

## 2. 指标纯函数

- [x] 2.1 新建 `backend/tools/keypoint_metrics.py`，全部为无 I/O 纯函数
- [x] 2.2 实现逐关节逐帧欧氏距离序列与 `rmse_px`、`rmse_norm`
- [x] 2.3 实现 `pck(thresholds=[0.02,0.05,0.10])`，以参考体长为单位，不可见点不计入分母
- [x] 2.4 内置 COCO17 sigmas 常量表（`coco17.v1`）与 `oks()`；面积取 reference 可见关节包围盒，退化时回退 `(0.5×体长)^2` 并返回 `area_source`
- [x] 2.5 实现 ICC(2,1)：帧为 subject、标注员为 rater，x/y 分别计算，返回较小值
- [x] 2.6 实现逐关节排名（按 `rmse_norm` 降序）与 `aggregate.worst_three`

## 3. CLI 与报告

- [x] 3.1 新建 `backend/tools/eval_keypoints.py`：参数 `--reference`、`--candidate`、`--format {cvat,coco,normalized}`、`--out`
- [x] 3.2 增加 `--frame-space {annotation,source}`（默认 `annotation`）；两侧空间不一致时直接报错退出
- [x] 3.3 增加 `--baseline-out`、`--force`、`--reason`
- [x] 3.4 组装报告：八个顶层字段，`inputs` 记录路径/SHA-256/帧数，`pairing` 记录配对与丢弃
- [x] 3.5 JSON 落盘前校验不含 NaN/Infinity；失败时不写出部分文件
- [x] 3.6 增加 `--md-out`：输出人可读表（关节、n、rmse_px、rmse_norm、PCK 三档、OKS、ICC、排名）
- [x] 3.7 非零退出码与可定位错误信息：文件缺失、格式不支持、帧号空间冲突、参考尺度不可用

## 4. 基线治理

- [x] 4.1 `--baseline-out` 目标已存在且无 `--force` 时拒绝写入，退出码非零
- [x] 4.2 `--force` 必须同时提供 `--reason`，否则拒绝执行
- [x] 4.3 基线文件写入 `approval: {reason, at}`，并保留完整 `accuracy-report.v1` 内容

## 5. 测试

- [x] 5.1 `backend/tests/test_keypoint_metrics.py`：常量平移 50px → `rmse_px ≈ 50`（±1）
- [x] 5.2 偏移 0.03 体长 → 命中 PCK@0.05/0.10、不命中 PCK@0.02
- [x] 5.3 两份输入完全一致 → 各关节 `icc_x`/`icc_y` = 1.0（1e-6 容差）
- [x] 5.4 恒定系统偏移 → ICC 明显小于 1
- [x] 5.5 可见性为 false 的点不计入 PCK 分母
- [x] 5.6 包围盒退化 → `area_source=body_length_fallback` 且 `caveats` 含说明
- [x] 5.7 关节名写法不同（`left_shoulder` vs `left-shoulder`）被识别为同一关节
- [x] 5.8 COCO17 与 halpe26 混用 → 只评估交集，单侧关节进 `skipped_joints`
- [x] 5.9 参考体长对拍：tools 与 `compute_reference_body_length()` 在同一标注上差 ≤ 0.01 px
- [x] 5.10 `backend/tests/test_eval_keypoints_cli.py`：用 `kinematics_golden_v1/source/annotations.xml` 作为 reference，程序化构造 candidate（平移/丢帧），断言报告的 `pairing` 与 `per_joint` 字段
- [x] 5.11 CLI 输入不存在 → 非零退出且不产生输出文件
- [x] 5.12 基线已存在且无 `--force` → 拒绝写入且原文件 SHA-256 不变
- [x] 5.13 输入文件只读性：运行前后 reference/candidate 的 SHA-256 不变
- [x] 5.14 回归：不同 clip 出现相同帧号时不得配对（真实素材 119 帧 / 111 个不同帧号 / 8 个跨 clip 重复）
- [x] 5.15 回归：两侧配对键模式不一致时以 `key_mode_mismatch` 拒绝

## 6. 文档与收口

- [x] 6.1 在 `README_METRICS.md` 增加一节，说明这是评估工具而非生产指标，口径与生产参考尺度一致
- [x] 6.2 在 `backend/tools/` 增加简短 README：两种用法（人工 vs 人工、模型 vs 人工）与命令示例
- [ ] 6.3 全量跑 `python -m pytest -q` 确认既有测试不受影响
- [x] 6.4 `openspec validate add-keypoint-accuracy-benchmark --strict` 通过

## 验收命令

```bash
cd swim/backend
# 指标与 CLI 单测
python -m pytest -q tests/test_keypoint_metrics.py tests/test_eval_keypoints_cli.py

# 真实夹具上的自比对（应与自身完全一致）
python tools/eval_keypoints.py \
  --reference tests/fixtures/kinematics_golden_v1/source/annotations.xml \
  --candidate  tests/fixtures/kinematics_golden_v1/source/annotations.xml \
  --format cvat --out /tmp/self_report.json

# 回归
python -m pytest -q
```
