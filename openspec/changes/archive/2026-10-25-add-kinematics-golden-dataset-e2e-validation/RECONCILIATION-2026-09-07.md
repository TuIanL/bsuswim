# Change 对账报告：add-kinematics-golden-dataset-e2e-validation

- 对账日期：2026-09-07
- 对账对象：`openspec/changes/add-kinematics-golden-dataset-e2e-validation/tasks.md`（63/167 勾选，最后修改 2026-07-26）
- 对账基准：当前 `main` @ `61e4fb3`（2026-08-03）
- 方法：逐条把 tasks.md 的勾选状态与代码/测试实体对照，代码级取证（file:line）

---

## 一、总览

| 类别 | 条数 | 说明 |
|---|---|---|
| 勾选且**有代码/测试证据** | 58 | 真实落地 |
| 勾选但**证据不足**（理由为推断或引用了不存在的产物） | 5 | 3.9 / 14.3 / 14.4 / 14.5 / 0.7 |
| 未勾选但**实际已完成** | 2 | 15.1 / 15.2 |
| 未勾选且确认未做 | 102 | 与 tasks.md 一致 |

**结论：进度条基本可信，但存在 3 个"未勾选却已完成"与"已勾选却无证据"的错位，以及 3 个必须在动工前解决的阻塞级契约问题。**

---

## 二、已交付并确认（file:line 取证）

| 分组 | 证据 |
|---|---|
| 0.1–0.6 | `fixtures/kinematics_golden_v1/fixture_manifest.json` 含 fps=60 / fps_fraction="60/1" / 3840×2160 / total_frames=421 / SHA-256。**实测 shasum 与 manifest 完全一致**（video `c06e7176…`、xml `c76abfa6…`） |
| 1.1–1.3 | `source/annotations.xml`(226K) + `source/side_view_golden.mp4`(102M) 均在位 |
| 1.4 | CVAT 1.1 image 格式，mapping 已内联于 manifest `frame_mapping` |
| 1.5 | `README.md` 在位 |
| 1.6–1.8 | `__init__.py:101-147` `load()` 校验 SHA-256，缺失/不匹配抛 `GoldenFixtureError` 且明确不回退 synthetic |
| 2.1–2.10 | `tests/fixtures/golden_contract.py:17,32,44,50,59,78,87,100,112,130,176,196` — **10 个 helper 全部实现**，含 2.10 的 `assert_pdf_page_count` 与 `assert_pdf_semantic_markers` |
| 3.1–3.7, 3.10 | `tests/golden/test_cvat_golden_parser.py:38-103` 逐条覆盖 |
| 3.8 | `app/services/normalized_annotation_service.py:405-480` warnings 走 `all_warnings` 单一变量，无覆盖/无 NameError |
| 11.1–11.12 | `frontend-vue/src/views/PrintReportView.vue:5,14-21,56,82,115,145,184` + `printReadyRegistry.ts:30`；配套 `PrintReportView.spec.ts:76,112-124` 覆盖 signature、无条件 ready、error code |
| 13.8–13.10 | `page_builders.py:83-100` `_build_video_context()` 已改读 `SessionVideo.fps` / `.resolution`，`duration_sec` 硬编码 null，并注释说明 VideoFile 无这些列 |
| 13.1–13.7, 13.13 | 已在既有代码中落实（`media_probe.py`、`videos.py`、`SessionVideoCreate.fps`） |
| 14.1–14.2 | `artifact_projection.py:80` `collect_skipped_artifact_quality_notes()` 产出 `module_key/artifact_key/metric_keys/artifact_status`；`page_builders.py:72-80` `_filter_notes_by_modules()`，接入 3 个页面（:242 / :310 / :378）；测试 `test_kinematics_report.py:585-625` |

---

## 三、错位项（需要修正勾选）

### 3.1 未勾选但已完成 — 应补勾

| 任务 | 证据 |
|---|---|
| 15.1 重命名 `golden_five_page_report.json` → `synthetic_five_page_report_contract.json` | 新文件 `backend/tests/fixtures/synthetic_five_page_report_contract.json` 已存在；旧名在仓库中已无残留 |
| 15.2 删除自动写 baseline 逻辑 | `tests/test_kinematics_report.py` 与 `tests/test_report_interpretation.py` 中已无任何 `write_text` / `UPDATE_BASELINE` 写回 baseline 的代码 |

### 3.2 已勾选但无证据 — 应回退或改措辞

| 任务 | 问题 |
|---|---|
| **3.9** 「确认 ingest response 返回所有字段」 | 勾选理由写的是「已在 E2E 实测中验证」，但 `backend/tests/e2e/` **目录不存在**，仓库中没有任何 E2E 测试。该勾选无证据支撑 |
| **14.3 / 14.4 / 14.5** | 勾选理由写的是「过滤逻辑已确保」。实际只有 `_filter_notes_by_modules` 的**纯函数单测**，没有任何页面级断言证明「upper-limb 降级只出现在 P3」「P2/P4 不含 upper-limb 说明」 |
| **0.7** 「创建 fixture manifest」 | manifest 存在，但 `integrity.manifest_sha256` 仍是占位符 `"TBD"`，manifest 自身完整性未校验 |
| **1.7** 「加载时校验所有 SHA-256」 | 只校验 video + xml 两个文件；`expected_contracts` 与 `mutations` 声明的文件均不存在且不被校验（见 P0-3） |

---

## 四、P0 阻塞级问题（动工前必须先决策）

### P0-1 · frame mapping 契约三处互相矛盾

| 来源 | 声明 |
|---|---|
| `fixture_manifest.json` `frame_mapping` | `mode=affine`、`source_frame_offset=0`、`source_frame_stride=4`、`source_original_offset=270` |
| `proposal.md:12` + tasks **4.5 / 4.8 / 6.3** | `offset=32`、`stride=1`，source_video_frame 范围 **32..87** |
| 真实 `annotations.xml`（实测） | 105 个 `<image>`，id 1→105，原始帧 `frame_00000270` → `frame_00000690`；其中 **104 帧含 skeleton**（id=56 / 原始帧 490 缺骨架）。**间距非等距：101 段 ×4 + 2 段 ×8** |

后果：

- 「affine stride=4」只是近似模型。实测 annotation frame 104 → 相对视频帧 **420**，而 tasks 0.3 写的是 **416**，偏差 4 帧；两段 ×8 处会再各累积 4 帧漂移。
- 任何 `source_video_frame = annotation_frame * 4 + offset` 形式的断言都会在异常段失配。
- 依赖该数值的任务组 **4 / 6 / 9 共 27 条**在契约定死前无法编写，且 13.11 / 13.12 同样受影响。
- 「offset=32, stride=1, 32..87」这一组数与真实 XML 完全对不上（87 帧仅覆盖 1.45 秒），判断为早期迭代遗留的陈旧值，应删除。

**建议**：以真实 XML 为准，把 mapping 改为「显式帧号表」或「分段 affine」，并同步 manifest / proposal / tasks 三处。

### P0-2 · golden 视频未纳入版本库

```
.gitignore:26:  *.mp4
  → backend/tests/fixtures/kinematics_golden_v1/source/side_view_golden.mp4  (102 MB)
```

`git ls-files` 显示该 fixture 目录只有 4 个文件入库：`README.md`、`__init__.py`、`fixture_manifest.json`、`source/annotations.xml`。**视频仅存在于本机**。

而 `GoldenFixture.load()` 的设计是「缺失即 `GoldenFixtureError`，绝不回退 synthetic」——这意味着任何 fresh clone 或 CI runner 上跑 golden 测试**必然失败**。

这正是 tasks **16.7**（「若视频公开提交…若视频仅私有…」）这个未决分支决策的根源，也是 16.x 整组 12 条一直没动的原因。不先定视频分发模型，CI 集成无解。

### P0-3 · `expected/` 与 `mutations/` 为空目录，manifest 存在悬空引用

`fixture_manifest.json` 声明：

```json
"expected_contracts": {
  "ingest":  "expected/ingest_contract.json",
  "metrics": "expected/metric_contract.json",
  "report":  "expected/report_contract.json"
},
"mutations": {
  "missing_right_wrist": { "recipe": "mutations/missing_right_wrist.recipe.json" }
}
```

实测两个目录下**无任何文件**，而 `__init__.py:127-128` 只校验 `video` 与 `annotations` 两项，不校验这两类 → 静默悬空。

后果：Section 10（缺关节降级 E2E，10.1 起）缺少 mutation recipe 无法生成变体 XML；5.10 的「人工批准的 metric tolerance contract」与 9.x 的 expected contract 也无载体。

---

## 五、未做部分确认（与 tasks.md 一致）

| 分组 | 条数 | 落地现状 |
|---|---|---|
| 4 上传→normalized API 链路 | 10 | `backend/tests/e2e/` 不存在 |
| 5 完整 pipeline golden | 10 | 同上 |
| 6 Representative frames | 7 | 同上 |
| 7 五类视觉资产 | 10 | 同上 |
| 8 Review findings | 7 | 同上 |
| 9 五页报告契约 | 10 | 同上 |
| 10 缺关节降级 E2E | 10 | 缺 mutation recipe |
| 12 HTML/PDF 真实 E2E | 12 | 无 Playwright/pypdf 集成 |
| 13.11 / 13.12 | 2 | FPS/resolution 溯源断言未写 |
| 15.3 / 15.4 / 15.5 | 3 | synthetic 未被降级为「仅结构契约」测试；`tools/` 为空，无显式更新脚本 |
| 16 CI 集成 | 12 | 仅有既有 `.github/workflows/ci.yml`；`golden_contract` / `golden_e2e` marker 均未注册 |
| 17 文档与总验证 | 9 | 无 |

受 P0-1 / P0-2 阻塞、无法动工的合计 **71 条**（4+5+6+9+10+12+16）。

---

## 六、建议的处置顺序

1. **先解两个决策**：frame mapping 真值（P0-1）、golden 视频分发模型（P0-2）。这两条不定，剩余 71 条无法开工。
2. **补齐 fixture 契约载体**：落地 `expected/` 三个 contract 与 `mutations/` recipe，并让 loader 一并校验（P0-3）。
3. **修正 tasks.md 勾选**：补勾 15.1 / 15.2；3.9 与 14.3–14.5 回退为未勾选或改写为「实现完成、断言待补」。
4. **再决定路径 A / B / C**（收口归档 / 先啃 4.x / 就地冻结）。
