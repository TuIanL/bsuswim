# cvat-xml-parse (delta)

## ADDED Requirements

### Requirement: Real golden CVAT XML ingestion preserves the skeleton contract

系统 SHALL 在使用真实 CVAT Skeleton XML（如 `kinematics-golden.v1` fixture）经由 annotation ingest API 处理时，保持以下骨架契约，且 ingestion 过程不得因未定义变量而失败。

#### Scenario: Baseline golden XML is ingested without NameError

- **WHEN** 系统通过 annotation ingest API 处理真实 golden annotations.xml（CVAT sequence 356 帧、active 56 帧、COCO17 17 点、baseline 全 visible）
- **THEN** CVAT sequence frame count SHALL 为 356
- **AND** active annotated frame count SHALL 为 56
- **AND** active annotation frame range SHALL 为 0..55
- **AND** 每个 active frame SHALL 包含 17 个 COCO17 关节点
- **AND** all-outside track termination MUST NOT 形成额外 active frame
- **AND** ingestion SHALL NOT raise NameError from an undefined warning variable in the ingestion path

#### Scenario: Warnings aggregation uses a single reliable source

- **WHEN** ingestion path 汇总 parser warnings 与派生 warnings
- **THEN** 汇总 SHALL 使用真实存在的局部变量（`cvat_parsed.warnings` 与 `derived_warnings`）
- **AND** MUST NOT 引用未定义的裸 `warnings` 变量
- **AND** 持久化的 parse warnings SHALL 与该汇总一致
