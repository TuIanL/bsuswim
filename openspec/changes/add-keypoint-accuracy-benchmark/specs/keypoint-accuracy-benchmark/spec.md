## ADDED Requirements

### Requirement: 工具读取两份关键点并输出逐关节精度报告

系统 SHALL 提供只读命令行工具，接受 reference 与 candidate 两份关键点输入，按帧对齐后输出逐关节误差与一致性指标。

#### Scenario: 两份输入使用同一帧集合

- **WHEN** reference 与 candidate 各含 104 个相同帧号的关键点
- **THEN** 工具 SHALL 输出 `accuracy-report.v1` JSON
- **AND** `pairing.paired_frames` SHALL 为 104
- **AND** `pairing.dropped` SHALL 为 0
- **AND** `per_joint` SHALL 为每个双方共有的关节各给出一条记录

#### Scenario: 输入不可解析

- **WHEN** 输入文件不存在、格式无法识别或缺少必需字段
- **THEN** 工具 SHALL 以非零退出码结束
- **AND** SHALL 输出可定位错误的说明（文件路径 + 失败原因）
- **AND** MUST NOT 写出部分报告文件

### Requirement: 帧配对只取交集，并以稳定键识别同一帧

系统 SHALL 只评估两侧同时存在的帧，并记录被丢弃的帧数；MUST NOT 对缺失帧做插值或使用模型猜测。帧的身份 SHALL 以图像基名为主键（无基名时回退为稳定的图像 ID 或帧号字符串），MUST NOT 仅凭纯帧号跨 clip 配对。

#### Scenario: candidate 缺少部分帧

- **WHEN** candidate 只有 80 帧，reference 有 104 帧
- **THEN** 评估样本 SHALL 只使用这 80 帧
- **AND** `pairing.dropped` SHALL 为 24
- **AND** 报告中 SHALL NOT 出现任何由插值生成的帧

#### Scenario: 多 clip 合并后帧号重复

- **WHEN** 两份输入来自不同 clip，且恰好存在相同的帧号
- **THEN** 这些帧 MUST NOT 被判定为同一帧
- **AND** 若无任何共同图像基名，工具 SHALL 以非零退出码结束并说明无共同帧

#### Scenario: 两侧配对键模式不一致

- **WHEN** 一侧按图像基名配对，另一侧只有帧号
- **THEN** 工具 SHALL 以 `key_mode_mismatch` 拒绝评估
- **AND** MUST NOT 猜测对齐方式

### Requirement: 归一化基准与生产参考尺度同口径

系统 SHALL 使用与生产指标一致的参考尺度定义（两侧肩中点与两侧踝中点连线的逐帧距离中位数），并以该值作为归一化分母。

#### Scenario: 同一份标注的尺度一致

- **WHEN** 工具与生产计算器 `compute_reference_body_length()` 处理同一份标注
- **THEN** 两者输出的参考体长差 SHALL ≤ 0.01 px

#### Scenario: 参考尺度不可用

- **WHEN** 可用帧不足以计算参考体长
- **THEN** 工具 SHALL 以非零退出码结束
- **AND** SHALL NOT 退化为像素阈值继续评估

### Requirement: PCK 以参考体长为单位计算

系统 SHALL 计算 PCK@0.02、PCK@0.05、PCK@0.10 三档，判定门槛为「预测点与真值点的欧氏距离 ≤ 阈值 × 参考体长」。

#### Scenario: 偏移量落在两档之间

- **WHEN** 某关节某帧的预测点相对真值偏移 0.03 倍参考体长
- **THEN** 该点 SHALL 计入 PCK@0.05 与 PCK@0.10
- **AND** SHALL NOT 计入 PCK@0.02

#### Scenario: 关节在某一侧不可见

- **WHEN** 某帧该关节在任一输入中被标记为不可见
- **THEN** 该帧 MUST NOT 计入该关节的 PCK 分母
- **AND** SHALL 计入该关节的 `n` 缺口说明

### Requirement: OKS 使用 COCO17 sigmas 并声明面积来源

系统 SHALL 按 COCO17 的逐关节 sigma 计算 OKS，并在报告中声明所用目标面积的来源。

#### Scenario: 关键点包围盒可用

- **WHEN** reference 的可见关节可构成非退化包围盒
- **THEN** OKS SHALL 使用该包围盒面积
- **AND** `params.area_source` SHALL 为 `keypoint_bbox`

#### Scenario: 包围盒退化

- **WHEN** reference 的包围盒面积为 0 或低于有效下限
- **THEN** 工具 SHALL 回退为 `(0.5 × reference_body_length)^2`
- **AND** `params.area_source` SHALL 为 `body_length_fallback`
- **AND** `caveats` SHALL 包含该回退说明

### Requirement: ICC 以帧为 subject、标注员为 rater 计算

系统 SHALL 对每个关节分别对 x、y 坐标计算 ICC(2,1)（two-way random effects、absolute agreement、single measure），并报告两者的较小值。

#### Scenario: 两份输入完全一致

- **WHEN** candidate 与 reference 在每个关节每一帧上完全相同
- **THEN** 该关节 `icc_x` 与 `icc_y` SHALL 均为 1.0（允许浮点容差 1e-6）

#### Scenario: 两份输入存在恒定系统偏移

- **WHEN** candidate 在所有帧上相对 reference 平移固定 50 px
- **THEN** 该关节 ICC SHALL 显著小于 1
- **AND** `rmse_px` SHALL 约等于 50（容差 ±1）

### Requirement: 跨 schema 按关节名映射，不猜测缺失关节

系统 SHALL 通过规范化关节名（小写、下划线/空格统一为连字符）在 COCO17 与 halpe26 之间建立映射；无法映射的关节 MUST NOT 被补点或猜测。

#### Scenario: 两种 schema 存在公共子集

- **WHEN** reference 为 COCO17、candidate 为 halpe26
- **THEN** 只有双方共有的关节 SHALL 参与评估
- **AND** 仅单侧存在的关节 SHALL 列入 `skipped_joints`
- **AND** `skipped_joints` 中每个关节 SHALL 附带跳过原因

#### Scenario: 关节名写法不同

- **WHEN** 一侧写作 `left_shoulder`，另一侧写作 `left-shoulder`
- **THEN** 两者 SHALL 被识别为同一关节

### Requirement: 报告结构固定且带 schema 版本

系统 SHALL 输出 `accuracy-report.v1`，包含 `schema_version`、`inputs`、`pairing`、`params`、`per_joint`、`aggregate`、`skipped_joints`、`caveats` 八个顶层字段。

#### Scenario: 报告被校验

- **WHEN** 工具成功完成一次评估
- **THEN** 报告 SHALL 包含上述八个顶层字段
- **AND** `inputs` 中每个文件 SHALL 记录路径、SHA-256 与实际帧数
- **AND** `aggregate.worst_three` SHALL 按 `rmse_norm` 从大到小列出三个关节
- **AND** 报告 SHALL 通过 JSON 解析且不含 NaN/Infinity

### Requirement: 基线文件不自动覆盖

系统 SHALL 在写入 `accuracy_baseline.json` 时禁止隐式覆盖；已存在的基线只能通过显式 `--force` 与 `--reason` 更新。

#### Scenario: 目标基线已存在

- **WHEN** `--baseline-out` 指向已存在的文件且未提供 `--force`
- **THEN** 工具 SHALL 以非零退出码结束
- **AND** MUST NOT 修改该文件

#### Scenario: 显式强制更新

- **WHEN** 同时提供 `--force` 与 `--reason "<change-id>"`
- **THEN** 基线 SHALL 被更新
- **AND** 文件内 `approval` 字段 SHALL 记录该 reason 与时间戳

### Requirement: 工具只读且可离线运行

系统 SHALL 在不连接数据库、不启动 FastAPI 运行时的前提下完成评估，且 MUST NOT 修改输入文件或生产数据。

#### Scenario: 离线执行

- **WHEN** 在没有数据库连接与环境变量的机器上运行工具
- **THEN** 评估 SHALL 正常完成

#### Scenario: 输入文件不被修改

- **WHEN** 工具运行结束
- **THEN** reference 与 candidate 文件的 SHA-256 SHALL 与运行前一致
