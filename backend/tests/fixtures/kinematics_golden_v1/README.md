# kinematics-golden.v1 Fixture

版本化真实衍生 golden fixture，用于端到端验证二维运动学分析完整链路。

## 素材来源

- **视频**: 侧面游泳视频片段，3840×2160, 60fps, h264, ~7秒, 421帧
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
| 标注帧范围 | annotation frame 0..104 (缺 frame 55) |
| 帧映射模式 | affine |
| source_frame_offset | 0 |
| source_frame_stride | 4 |
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
│   └── side_view_golden.mp4       # 脱敏侧面视频
├── expected/
│   ├── ingest_contract.json       # 解析&标准化契约
│   ├── metric_contract.json       # 运动学指标数值契约
│   └── report_contract.json       # 报告结构契约
└── mutations/
    └── missing_right_wrist.recipe.json  # 缺失关节点变体
```

## 帧映射说明

```
annotation_frame N  →  source_video_frame (N * stride + offset)
                    →  source_video_frame (N * 4)

annotation_frame 0  →  video frame 0
annotation_frame 1  →  video frame 4
...
annotation_frame 104 →  video frame 416
```

原视频帧号（来自 CVAT 导出文件名）从 270 开始：`frame_00000270.jpg`。
视频 `side_view_golden.mp4` 已从该帧裁剪，因此 offset=0。

## Baseline 管理

- Golden baseline 由 `fixture_manifest.json` 锁定，**禁止自动更新**
- 更新 expected contract 必须通过 `scripts/build_kinematics_golden_fixture.py` 生成候选基线，
  再由 `scripts/approve_kinematics_golden_baseline.py` 人工审批
- CI 只能读取 baseline，不得修改

## 使用方式

```bash
# Golden contract tests (每 PR 硬门禁)
pytest backend/tests/golden/ -m golden_contract -v

# Full-stack E2E tests (nightly/release 门禁)
pytest backend/tests/e2e/ -m golden_e2e -v
```
