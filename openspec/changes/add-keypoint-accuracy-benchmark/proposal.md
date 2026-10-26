## Why

系统目前没有任何"与真值比较"的度量。`backend/tests/` 下 35 个测试文件全部是契约测试（schema 字段、页数、降级行为），`PCK` / `OKS` / `RMSE` / `ICC` 在代码库中零实现。后果是：换一个姿态模型、加一层平滑滤波、调一个参考尺度，都无法回答"比原来准了多少"。

下一阶段的两条主线都卡在这个前提上——信号质量层（平滑/飞点剔除）需要基线来定"变化多少算合理"，自动姿态基线（YOLO11x-pose / RTMPose）需要基线来判断"离人工上限还差多远"。因此先建立一把尺子，再谈改进。

## What Changes

- 新增只读命令行工具 `backend/tools/eval_keypoints.py`：给定同一段视频的两份关键点（reference 与 candidate），输出逐关节误差与整体一致性指标。
- 支持三种输入来源：CVAT Skeleton XML、COCO keypoints JSON、已归一化的 `keypoint_frames` JSON。
- 计算四类指标：逐关节归一化 RMSE、PCK@0.02/0.05/0.10（以参考体长为单位）、OKS（COCO17 sigmas）、ICC(2,1)（重测/双标注一致性），并给出逐关节排名。
- 输出机器可读的 `accuracy_report.json`（含 schema 版本、输入指纹、样本口径）与人可读的 markdown 表。
- 提供 `--baseline-out` 把某次结果固化为 `accuracy_baseline.json`，供后续阶段做回归比较。
- 明确边界：不修改生产分析流水线、不访问数据库、不训练或推理任何模型、不改动现有测试与 CI 门禁。

## Capabilities

### New Capabilities

- `keypoint-accuracy-benchmark`: 定义关键点精度的度量口径与输出契约——归一化基准、阈值单位、指标定义、逐关节报告结构、基线文件格式与不可变性规则。

### Modified Capabilities

无。本 Change 只新增一个独立评估能力，不改变任何现有能力的运行时行为；现有规格与 CI 门禁保持不变。

## Impact

### 新增文件

- `backend/tools/__init__.py`
- `backend/tools/eval_keypoints.py` — CLI 入口、参数校验、报告输出
- `backend/tools/keypoint_metrics.py` — 纯函数：RMSE / PCK / OKS / ICC / 排名
- `backend/tools/keypoint_sources.py` — 三种输入的读取与统一为 `{frame: {joint: (x, y, visible)}}`
- `backend/tests/test_keypoint_metrics.py` — 指标单元测试（含已知答案用例）
- `backend/tests/test_eval_keypoints_cli.py` — CLI 端到端（用现有 fixture 造两份标注）

### 复用既有资产

- `backend/tests/fixtures/kinematics_golden_v1/source/annotations.xml`（104 帧真实标注）作为 reference
- `backend/tests/fixtures/kinematics_golden_v1/source/frame_mapping.json` 用于帧号对齐校验
- `backend/tests/fixtures/kinematics_golden_v1/fixture_manifest.json` 提供参考体长与 FPS 口径

### 不影响

- 生产代码路径（`app/` 下不改一行）
- 现有 pytest 门禁与 `.github/workflows/`（新测试走普通 marker，不新增 CI job）
- 数据库与迁移
