# kinematics-golden.v1 Fixture

版本化真实衍生 golden fixture，用于端到端验证二维运动学分析完整链路。

## 素材来源

- **视频**: 侧面游泳视频片段，3840×2160, 60fps, h264, ~7秒, 421帧，仓库内压缩后约20MB
- **标注**: CVAT 1.1 skeleton 标注（image-based 格式），COCO17 关节点，标注标签为 `person`

## 授权与隐私

- 素材由项目组成员制作，已获使用授权
- 视频已脱敏处理，不含可识别个人身份信息
- 仅供项目内部测试使用，不得作为公开数据集分发

## 关键参数

| 参数 | 值 |
|------|-----|
| FPS | 60 (60/1) |
| 分辨率 | 3840×2160 |
| 标注帧数 | 104 (共105 images, 1个无skeleton) |
| 标注帧范围 | annotation frame 0..104 (缺 skeleton frame 94) |
| 缺失 skeleton | annotation frame 94 / 原始 frame 650 |
| 帧映射模式 | explicit |
| source_original_offset | 270 |
| effective annotation FPS | 15 |
| 关节点 | COCO17 (nose, left/right eyes/ears/shoulders/elbows/wrists/hips/knees/ankles) |
| 标注标签 | person |

## 目录结构

```
kinematics_golden_v1/
├── README.md
├── fixture_manifest.json          # Golden fixture 元数据与校验
├── source/
│   ├── annotations.xml            # CVAT 1.1 标注文件
│   ├── frame_mapping.json         # XML image 到视频帧的显式映射
│   └── side_view_golden.mp4       # 脱敏侧面视频
├── expected/
│   ├── ingest_contract.json       # 解析&标准化契约
│   ├── metric_contract.json       # 运动学指标数值契约
│   └── report_contract.json       # 报告结构契约
└── mutations/
    └── missing_right_wrist.recipe.json  # 缺失关节点变体
```

## 帧映射说明

`frame_mapping.json` 逐条记录 annotation frame、XML 原始帧号、裁剪视频帧号和是否存在 skeleton。大多数相邻标注间隔为 4，但 `490 → 498` 存在一次 8 帧间隔，因此不能使用一个全局 `stride=4` 的 affine 映射。

原始帧号（来自 CVAT 导出文件名）从 270 开始，裁剪视频帧号为 `source_original_frame - 270`。缺失 skeleton 的 image 仍保留在映射中，但不会进入 active annotation frame。

## Baseline 管理

- Golden baseline 由 `fixture_manifest.json` 锁定，**禁止自动更新**
- 视频采用压缩后的本地 fixture 直接随仓库分发，保持原始分辨率、帧率和总帧数，避免 Git LFS/私有 artifact 依赖
- 当前 `expected/` 文件是结构化的待批准候选契约（`pending_runtime_approval`）；真实完整 pipeline 的数值、artifact 和 PDF baseline 仍需在具备全栈环境后显式批准
- 更新 expected contract 必须通过 `scripts/build_kinematics_golden_fixture.py` 生成候选基线，
  再由 `scripts/approve_kinematics_golden_baseline.py` 人工审批
- CI 只能读取 baseline，不得修改

## 使用方式

```bash
# Golden contract tests (每 PR 硬门禁)
python -m pytest -q backend/tests/golden/ -m golden_contract -v

# Full-stack E2E tests (nightly/release 门禁)
pytest backend/tests/e2e/ -m golden_e2e -v
```
