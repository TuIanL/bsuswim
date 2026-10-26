# 对账报告：add-kinematics-golden-dataset-e2e-validation

- 对账日期：2026-10-25
- 取代：`RECONCILIATION-2026-09-07.md`（该报告的两个 P0 已闭环，结论不再适用）
- 方法：逐条把规格要求与代码/测试实体对照，代码级取证（file:line）；多关键词检索统一用 `grep -E`，避免 BSD grep 不支持 `\|` 导致的假阴性

## 一、结论

| 维度 | 状态 |
|---|---|
| 原 167 项任务 | 2026-09-09 已主动收敛为可维护门禁，**不是遗留待办** |
| 规格与实现的偏差 | **6 条要求无实现/无断言**，已删除；**4 处陈旧数值**，已修正 |
| 能力清单 | proposal 原列 9 项 modified capability，实际只有 3 份 delta spec，已收敛 |
| 陈旧映射假设 | `offset=32 / stride=1 / 0..55 / 32..87 / 356 帧` 全部与真实 fixture 不符，已删除 |
| 真实空缺 | 数值基线未批准、页面级断言缺失、E2E 仅 nightly |

## 二、陈旧数值修正（规格与实现不符）

| 位置 | 原值 | 实测值 | 证据 |
|---|---|---|---|
| active frame 数 | 56 | **104** | `annotations_merged.xml` 105 个 `<image>`，104 带骨架 |
| active frame range | 0..55 | **0..104** | 同上 |
| CVAT sequence 帧数 | 356 | 未断言（不再声明） | 测试只断言 manifest 值 |
| frame mapping | affine，offset=32，stride=1 | **explicit 帧号表**，`source_original_offset=270`，effective 15fps | `fixture_manifest.json` + `source/frame_mapping.json` |
| representative frame 范围 | 0..55 / 32..87 | 要求已删除 | 见下 |

补充证据：`annotations_merged.xml` 帧号 270→690，相邻间隔 `{4, 8}`（101 段 ×4 + 1 段 ×8），因此单条 affine stride 必然漂移——这正是 2026-09 把 mapping 改为 explicit 的原因。

## 三、删除的要求（无实现或无断言）

| 要求 | 判定依据 |
|---|---|
| **Representative frames reference valid source data** | `assert_representative_frame_valid` 仅定义于 `tests/fixtures/golden_contract.py:78`，全仓无任何调用点 |
| **时间序列单调 / 相邻帧连续性** | `assert_time_series_ordered`、`assert_adjacent_frame_continuity` 同样**从未被调用** |
| **角度位于 [0,180]、sample_count 上限** | `golden_contract.py` 无角度范围逻辑；`geometry.py` 无 clamp；无断言 |
| **key-set SHA-256 锁定** | `expected/metric_contract.json` 只有 `canonical_keys_source`，无 hash 字段；`status=pending_runtime_approval` |
| **资产 URL 返回 HTTP 200 + MIME 一致** | 只断言 URL 含 `/uploads/`（`test_kinematic_artifacts.py:326`），无 HTTP 取回与 Content-Type 比对 |
| **findings evidence metric/frame 有效性** | 只断言 `FindingSet.status == "ready"`（`test_golden_analysis_contract.py:115`），无逐条 evidence 校验 |
| **页面级 quality note 隔离（P2/P4 MUST NOT）** | 只有模块级过滤（`page_builders._filter_notes_by_modules`）与纯函数单测，无页面级断言 |
| **metric categories 独立断言** | `assert_metric_categories` 从未被调用；category 由 `CANONICAL_KEYS` 映射唯一确定 |

## 四、保留的要求与证据

| 要求 | 证据 |
|---|---|
| fixture 版本化与不可变 | `tests/golden/test_fixture_contract.py`（6 项，含路径逃逸与 hash 不匹配） |
| 真实 CVAT 解析契约 | `tests/golden/test_cvat_golden_parser.py`（8 项） |
| 显式帧映射 | `fixture_manifest.json` `frame_mapping.mode=explicit` + `frame_mapping.json` |
| 指标集合与计算器一致 | `test_kinematics_report.py` 使用 `assert_canonical_metric_keys` |
| 数值安全（无 NaN/Inf） | `assert_finite_numbers` 在 golden 与服务测试中均被调用 |
| 五类资产文件可核验 | `test_golden_analysis_contract.py:120-127`；URL 路径 `test_kinematic_artifacts.py:326` |
| 五页报告契约 | `assert_five_page_contract`（golden + e2e） |
| 同 revision 贯穿 | `test_golden_analysis_contract.py:108-113` |
| 缺腕降级 | `test_golden_analysis_contract.py:143` |
| HTML/PDF 一致 + 5 页 | `tests/e2e/test_golden_full_stack.py:248-278` |
| 无依据结论拦截 | `assert_no_unsupported_claims`（golden + report 测试） |
| baseline 人工审批 | `scripts/build_kinematics_golden_fixture.py` / `approve_kinematics_golden_baseline.py` |
| synthetic 降级 | `tests/fixtures/synthetic_five_page_report_contract.json` 存在 |
| 视频元数据 provenance | `page_builders._build_video_context` 读 `SessionVideo`；上传侧 `routes/videos.py:38-44` ffprobe 探测 |

## 五、CI 现状

- `ci.yml`：每 PR 跑 `pytest tests/golden -m golden_contract`（硬门禁）。
- `golden-e2e.yml`：`schedule: 0 18 * * *`（北京时间 02:00）+ `workflow_dispatch`，含 Postgres / Chromium / ffmpeg / 活栈前后端。
- `pytest.ini`：`norecursedirs = e2e`，默认测试不执行 E2E；且未设 `GOLDEN_E2E_ENABLED=1` 时测试**直接失败而非跳过**（防止静默通过）。

## 六、仍然真实的空缺（不写入规格承诺）

1. `expected/metric_contract.json` 的数值包络未人工批准，`status` 仍为 `pending_runtime_approval`。
2. 页面级 quality note 隔离无断言。
3. full-stack E2E 仅 nightly，不是每 PR 门禁。
4. `tasks.md` 0.6 曾记录原始 102 MB 视频的 SHA（`c06e7176…`），现 manifest 为 20 MB 重编码版（`d2addb2b…`）；本条已在 tasks.md 重写时移除。

## 七、验证

```bash
cd swim/backend
python -m pytest -q tests/golden -m golden_contract
```
