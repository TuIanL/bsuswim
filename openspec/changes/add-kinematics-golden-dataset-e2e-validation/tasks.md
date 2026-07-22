## 0. Confirm and freeze the golden source

- [ ] 0.1 核验真实视频 FPS、分辨率和总帧数
- [ ] 0.2 核验 annotation frame 0 是否确实对应 source video frame 32
- [ ] 0.3 核验 annotation frame 55 是否对应 source video frame 87
- [ ] 0.4 确认视频与 XML 可用于测试仓库或受控 CI artifact
- [ ] 0.5 记录隐私审批与素材来源
- [ ] 0.6 计算视频、XML 和 manifest SHA-256
- [ ] 0.7 创建 `kinematics-golden.v1` fixture manifest（含 frame_mapping.verification 人工 anchor 证据与 FPS 有理数表示）

## 1. Add real-derived golden fixture package

- [ ] 1.1 新增 `backend/tests/fixtures/kinematics_golden_v1/`
- [ ] 1.2 放入真实 CVAT `annotations.xml`
- [ ] 1.3 放入对应的脱敏侧面视频
- [ ] 1.4 放入 `instances_default.json` 或精简映射 manifest
- [ ] 1.5 新增 fixture README，说明坐标、FPS、frame mapping 和授权边界
- [ ] 1.6 新增 fixture integrity loader
- [ ] 1.7 fixture 加载时校验所有 SHA-256
- [ ] 1.8 fixture 缺失或 checksum 不匹配时直接失败，不回退到 synthetic fixture

## 2. Add golden contract helpers

- [ ] 2.1 实现 recursive JSON finite-number assertion
- [ ] 2.2 实现 canonical metric key/category assertion（与 calculator.CANONICAL_KEYS 完全一致，不写死数量）
- [ ] 2.3 实现 time-series ordering assertion
- [ ] 2.4 实现 adjacent-frame continuity assertion
- [ ] 2.5 实现 representative-frame validity assertion
- [ ] 2.6 实现 source-revision trace assertion
- [ ] 2.7 实现 artifact file/checksum/MIME assertion
- [ ] 2.8 实现 report five-page assertion
- [ ] 2.9 实现 unsupported-claim assertion
- [ ] 2.10 实现 PDF page count（严格 ==5）和 semantic marker assertion

## 3. Harden real CVAT ingestion where required

- [ ] 3.1 使用完整真实 XML 运行 parser，而不是当前简化 fixture
- [ ] 3.2 断言 CVAT task frame count 为 356
- [ ] 3.3 断言 active annotated frames 为 56
- [ ] 3.4 断言 active frame range 为 0..55
- [ ] 3.5 断言每个 active frame 有 17 个 COCO17 关节点
- [ ] 3.6 断言 baseline visibility 全部为 visible
- [ ] 3.7 断言 all-outside track termination 不产生重复 active frame
- [ ] 3.8 修复 `normalized_annotation_service.py` 中 warnings 变量覆盖导致的 NameError（统一为可靠来源）
- [ ] 3.9 确认 ingest response 返回 normalized_annotation_id、revision、parse summary、quality 和 module readiness
- [ ] 3.10 验证 metadata 中保存 annotation coverage 与 verified frame mapping

## 4. Add upload-to-normalized-annotation integration test

- [ ] 4.1 通过 API 创建 coach、athlete 和 freestyle session
- [ ] 4.2 通过 `/videos/upload` 上传 golden MP4
- [ ] 4.3 通过 `/sessions/{id}/videos` 绑定 side video 并传入 fixture FPS
- [ ] 4.4 通过 multipart ingest endpoint 上传 annotations.xml
- [ ] 4.5 提交 confirmed affine mapping offset=32、stride=1
- [ ] 4.6 校验 AnnotationFile 状态为 parsed
- [ ] 4.7 校验 NormalizedAnnotation revision=1
- [ ] 4.8 校验 source_video_frame 范围为 32..87
- [ ] 4.9 校验 timestamp 与 fixture FPS 一致
- [ ] 4.10 校验上传和解析均使用真实 StorageService 文件

## 5. Add full annotation pipeline golden test

- [ ] 5.1 通过 `/analysis/submit` 提交 annotation_kinematics task
- [ ] 5.2 等待或同步执行完整 pipeline
- [ ] 5.3 断言任务 completed、stage=completed、progress=100
- [ ] 5.4 断言 ModelServiceClient 未被调用
- [ ] 5.5 断言 AnnotationMetric 使用 side_2d_kinematics
- [ ] 5.6 断言 summary 包含全部 canonical metric keys（集合相等 + category 一致）
- [ ] 5.7 断言 metric categories 恰好为 body_posture、upper_limb、lower_limb、head_trunk
- [ ] 5.8 断言 metrics payload 不含 NaN 或 Infinity
- [ ] 5.9 对受检角度执行范围和连续性断言
- [ ] 5.10 校验人工批准的 metric tolerance contract

## 6. Validate representative frames

- [ ] 6.1 遍历全部非空 representative_frames
- [ ] 6.2 验证 annotation_frame 在 0..55
- [ ] 6.3 验证 source_video_frame = annotation_frame + 32
- [ ] 6.4 验证 source_video_frame 在 32..87
- [ ] 6.5 验证 referenced annotation frame 确实存在
- [ ] 6.6 验证 extractable frame 能从视频精确解码
- [ ] 6.7 验证 unavailable metric 不声明 extractable representative frame

## 7. Validate five artifact classes

- [ ] 7.1 断言 ArtifactSet source revision 与 annotation 一致
- [ ] 7.2 断言五种 artifact type 均存在
- [ ] 7.3 断言至少一个 annotated keyframe 为 ready
- [ ] 7.4 断言 time-series、trajectory、range 和 radar 图为 ready
- [ ] 7.5 验证每个 ready artifact 文件存在且非空
- [ ] 7.6 验证实际文件 checksum
- [ ] 7.7 验证 public artifact URL 返回 200
- [ ] 7.8 验证 response MIME 与数据库 MIME 一致
- [ ] 7.9 验证 artifact annotation/source frame 均合法
- [ ] 7.10 禁止对渲染结果使用跨平台固定文件 hash

## 8. Validate review findings

- [ ] 8.1 断言 FindingSet status=ready
- [ ] 8.2 断言 rule_set=side_2d_kinematics_v1
- [ ] 8.3 断言 findings 和 skipped rules 均为合法结构
- [ ] 8.4 验证每个 evidence metric 指向已存在的 canonical metric
- [ ] 8.5 验证每个 evidence frame 位于有效帧范围
- [ ] 8.6 验证 finding source revision 与 metric/annotation 一致
- [ ] 8.7 验证所有 findings 保持 status=review_required

## 9. Validate the five-page report

- [ ] 9.1 断言 schema_version=swim-report.v1
- [ ] 9.2 断言 report_profile=side_2d_kinematics_5page_v1
- [ ] 9.3 断言 sections 数量严格等于 5
- [ ] 9.4 断言 page_number 恰好为 [1,2,3,4,5]
- [ ] 9.5 断言 page_type 顺序符合固定 profile（含 P2=body_posture_head_trunk 合并）
- [ ] 9.6 断言 section metrics、assets 和 findings 均可追溯
- [ ] 9.7 断言 source_trace 包含 metric、artifact、finding 和 assembler
- [ ] 9.8 断言所有 source revision 相同
- [ ] 9.9 执行 unsupported-claim guard
- [ ] 9.10 确认速度、划幅、SWOLF、推进力等仅可出现在 limitation 中

## 10. Add missing-joint degradation E2E

- [ ] 10.1 新增 XML mutation helper
- [ ] 10.2 将所有 active frame 的 right-wrist 设为 outside=1
- [ ] 10.3 用变体 XML 创建第二条完整 E2E 链路
- [ ] 10.4 断言 ingest 和 pipeline 仍成功
- [ ] 10.5 断言 right_elbow_angle_deg unavailable
- [ ] 10.6 断言 left_elbow_angle_deg 仍可用
- [ ] 10.7 断言其他三个模块不被错误 blocked
- [ ] 10.8 断言 right elbow keyframe 可以 skipped
- [ ] 10.9 断言 ArtifactSet 可以 partial
- [ ] 10.10 断言五页报告仍然存在，P3 含质量说明，P2/P4 不含 upper-limb 专项说明

## 11. Correct the five-page print contract

- [ ] 11.1 删除 PrintReportView 的额外 cover page
- [ ] 11.2 直接按 ReportData 的五个 sections 输出五个 print page
- [ ] 11.3 为每页增加 data-page-number、data-page-type、data-module-key
- [ ] 11.4 为根节点增加 data-report-generation-signature
- [ ] 11.5 增加每页稳定 PDF semantic marker
- [ ] 11.6 删除 finally 中无条件设置 `__REPORT_PRINT_READY__`
- [ ] 11.7 仅在 registry 完成后设置 ready
- [ ] 11.8 失败时设置 `__REPORT_PRINT_ERROR__`
- [ ] 11.9 Playwright 遇到 print error 或 timeout 时导出失败
- [ ] 11.10 增加布局溢出预检，溢出设置 `PRINT_LAYOUT_OVERFLOW` 并阻止导出
- [ ] 11.11 调整 CSS `.print-page { break-after: page }` 与 `:last-child { break-after: auto }`
- [ ] 11.12 增加 PrintReportView 单元测试：5 sections → 5 print pages

## 12. Add actual HTML/PDF E2E

- [ ] 12.1 启动真实 PostgreSQL 后端
- [ ] 12.2 构建并启动 Vue 前端
- [ ] 12.3 用 Playwright 打开普通 HTML 报告页
- [ ] 12.4 断言 HTML 中存在五个 section 及相同 generation signature
- [ ] 12.5 调用真实 PDF export endpoint
- [ ] 12.6 下载生成的 PDF
- [ ] 12.7 断言 PDF status=exported
- [ ] 12.8 断言 PDF 文件存在、非空且版本号增加
- [ ] 12.9 使用 pypdf 解析 PDF 断言页数严格等于 5
- [ ] 12.10 验证五页 semantic marker（ASCII 格式 `P3 | upper_limb_kinematics`，避免依赖中文字体文本提取）和标题
- [ ] 12.11 验证 HTML、print-data 和 PDF 的页序一致
- [ ] 12.12 验证 ready artifact 在 HTML 和 print route 中均可访问

## 13. Video FPS and metadata provenance

- [ ] 13.1 后端在视频上传时 ffprobe 探测 FPS 与 resolution
- [ ] 13.2 扩展 `VideoUploadResponse` 返回 `probed_fps` / `resolution`，并标记 `metadata_source=ffprobe`、`verified=true`
- [ ] 13.3 使用 ffprobe 在 fixture 制作期探测 golden video FPS 并写入 manifest（有理数 + value + source + verified）
- [ ] 13.4 验证视频绑定将 FPS 持久化到 SessionVideo.fps
- [ ] 13.5 更新 guided Web 上传流程，绑定 side video 时透传上传响应返回的 FPS/resolution
- [ ] 13.6 不把兼容性 fallback 60.0 当作 verified FPS
- [ ] 13.7 记录 fps_source 与 fps_verified 到 normalized annotation metadata
- [ ] 13.8 修复 `_build_video_context()`（`reporting/kinematics_report/page_builders.py`）读取 `SessionVideo.fps` 作为权威 FPS
- [ ] 13.9 修复 `_build_video_context()` 读取 `SessionVideo.resolution` 而非未声明 `VideoFile.width/height`
- [ ] 13.10 无权威持久化时长时 duration_sec 置为 null；video context 文件身份只用 `VideoFile.id` 与 `original_filename`
- [ ] 13.11 新增 golden 断言：report.context.video.fps == 绑定 SessionVideo.fps
- [ ] 13.12 新增 golden 断言：report.context.video.resolution == SessionVideo.resolution
- [ ] 13.13 不修改其他 report profile；审计其他 profile 是否在确认后另开 Change

## 14. Module-scoped artifact quality notes

- [ ] 14.1 在 `artifact_projection.collect_skipped_artifact_quality_notes()` 中丰富 note，增加 `artifact_key`、`module_key`、`metric_keys`、`artifact_status` 字段
- [ ] 14.2 在 `page_builders` 各 `build_*_page` 中按本页 source_module_keys 过滤 `artifact_quality_notes`
- [ ] 14.3 断言 upper-limb 资产降级只出现在 P3 upper_limb_kinematics
- [ ] 14.4 断言 P2 body_posture_control 与 P4 lower_limb_kinematics 不含 upper-limb 专项说明
- [ ] 14.5 断言 P5 review_and_retest 可汇总整体降级但不作为主断言目标

## 15. Demote existing synthetic snapshot

- [ ] 15.1 将 `golden_five_page_report.json` 重命名为 `synthetic_five_page_report_contract.json`
- [ ] 15.2 删除普通 pytest 中自动写 baseline 的逻辑
- [ ] 15.3 将旧测试降级为 synthetic structure contract（仅断言 schema_version、report_profile、sections 数量、page_number、page_type）
- [ ] 15.4 更新仅通过显式脚本执行
- [ ] 15.5 确认与 `kinematics_golden_v1/expected/` 新 fixture 不共享 baseline

## 16. CI integration

- [ ] 16.1 注册 `golden_contract` pytest marker
- [ ] 16.2 注册 `golden_e2e` pytest marker（发布级硬门禁）
- [ ] 16.3 新增 PostgreSQL test service
- [ ] 16.4 安装 Chromium 和 Playwright dependencies
- [ ] 16.5 安装视频解码依赖（pypdf 用于 PDF 解析）
- [ ] 16.6 为每个测试使用隔离 UPLOAD_DIR
- [ ] 16.7 根据 P0 fixture 发布模型拆分门禁：若视频公开提交，则 `golden_contract`（真实 XML + 视频 + 非浏览器依赖）为每个 PR 硬门禁；若视频仅私有，则 `golden_contract` 拆分为「每 PR：真实 XML + 固定 normalized fixture + 非视频依赖」与「可信分支/nightly/release：私有视频 + 解码 + artifacts + HTML/PDF full E2E」
- [ ] 16.8 nightly/manual release check 运行 full golden E2E
- [ ] 16.9 连续约 20 次误报率足够低后，将 golden_e2e 升级为受保护分支 required check
- [ ] 16.10 基础设施失败标记为独立 `E2E_INFRA_ERROR`，允许自动重试一次，重试仍失败继续阻断发布并区分 product assertion failed 与 environment setup failed
- [ ] 16.11 CI 失败时上传 PDF、HTML、ReportData 和任务状态作为 artifact
- [ ] 16.12 CI 不得自动接受新的 golden baseline

## 17. Documentation and final verification

- [ ] 17.1 编写 fixture 制作与隐私说明
- [ ] 17.2 编写 baseline 更新流程
- [ ] 17.3 编写本地 E2E 环境启动说明
- [ ] 17.4 运行全部 parser tests
- [ ] 17.5 运行全部 metrics/artifact/finding/report tests
- [ ] 17.6 运行 golden contract suite
- [ ] 17.7 运行 full golden E2E
- [ ] 17.8 运行 Vue build 和前端测试
- [ ] 17.9 验证 OpenSpec
