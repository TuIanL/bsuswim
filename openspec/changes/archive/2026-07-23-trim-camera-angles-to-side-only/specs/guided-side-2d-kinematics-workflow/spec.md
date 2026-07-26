## MODIFIED Requirements

### Requirement: Primary flow fixes to side camera and CVAT

主流程 SHALL 仅呈现并突出侧面机位，并将主标注入口固定为 CVAT Skeleton XML（`.xml`）。上传步骤 SHALL 仅提供侧面机位的上传入口，不得向用户展示任何其他机位（如正面、俯视、水下、半水下）的可选入口，也不得展示"后续扩展机位"之类的占位区域。

#### Scenario: Only side camera is presented on the upload page

- **WHEN** 用户进入一次训练记录的上传页
- **THEN** 系统 MUST 仅展示侧面视频上传入口
- **AND** 系统 MUST NOT 展示正面、俯视、水下、半水下等任何其他机位的卡片、选项卡或"后续扩展"占位区域

#### Scenario: Primary annotation source restricted

- **WHEN** 用户选择标注文件
- **THEN** 系统 MUST 仅允许 `source=cvat` 且具有有效 parsed 状态、side 视角、非空 normalized_annotation_id 的标注被选择
