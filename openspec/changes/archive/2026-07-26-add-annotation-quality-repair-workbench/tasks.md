## 1. 后端修复契约

- [x] 1.1 定义质量修复请求/响应 schema，覆盖 `expected_revision`、scale、waterline、swim_direction、events 和 frame_mapping，并限制可写字段
- [x] 1.2 实现 scale 两点距离换算、正长度校验、视频 intrinsic 边界校验和有限值校验
- [x] 1.3 实现 waterline 两点校验并写入 `reference_lines.waterline.points`
- [x] 1.4 实现事件新增、去重、按 frame 排序和 `hand_entry` 最小字段校验
- [x] 1.5 复用 `FrameMappingOverride` 逻辑，实现 confirmed affine/identity mapping 和 `user_confirmed` provenance

## 2. Revision 与质量服务

- [x] 2.1 实现 quality repair service，读取当前 normalized annotation 并按白名单合并修复字段
- [x] 2.2 增加 `expected_revision` 冲突检测，冲突时不写入且返回 409
- [x] 2.3 保存成功时递增 revision，更新 `annotation_metadata` 的 repair provenance，并保留原始 AnnotationFile
- [x] 2.4 使用 source 对应 profile 运行完整 AnnotationQualityValidator，更新 quality 和 analysis readiness
- [x] 2.5 确保修复后的 quality.source_revision、分析输入快照和最新 annotation revision 一致

## 3. API 与质量问题 action

- [x] 3.1 新增 `POST /api/normalized-annotations/{id}/quality-repair` endpoint，执行 ownership check 和请求校验
- [x] 3.2 返回 normalized annotation identity、revision、quality、module readiness 和 analysis readiness
- [x] 3.3 为可修复 issue code 填充稳定的 `suggested_action.type`、label 和 payload
- [x] 3.4 对质量面板中的重复 scale/同类问题提供稳定 code 去重所需的响应结构
- [x] 3.5 保持现有 validate endpoint 的缓存逻辑，并验证 repair revision 会使旧质量缓存失效

## 4. 前端视频修复工作台

- [x] 4.1 扩展前端类型和 API client，加入 repair payload、repair response 和 suggested action 类型
- [x] 4.2 创建 `AnnotationQualityRepairWorkbench`，加载绑定 side video、显示加载失败状态和当前 annotation revision
- [x] 4.3 实现视频播放、暂停、时间轴定位、上一帧/下一帧和当前 source video frame 显示
- [x] 4.4 实现基于 intrinsic video 尺寸的画布坐标转换和可拖动端点
- [x] 4.5 实现标尺步骤：两点绘制、真实长度输入、pixels_per_meter 预览和保存前校验
- [x] 4.6 实现水面线步骤：两点绘制、当前帧预览和保存前校验
- [x] 4.7 实现游泳方向步骤：left-to-right/right-to-left 选择和当前值回显
- [x] 4.8 实现事件步骤：选择事件类型、按当前帧添加 hand_entry、编辑/删除草稿事件和至少两个事件提示
- [x] 4.9 实现帧映射步骤：显示 annotation/source frame 样例、offset/stride 输入和显式确认控件
- [x] 4.10 实现保存、取消、草稿重置、409 冲突刷新和保存后重新验证状态展示

## 5. 质量面板与工作流集成

- [x] 5.1 改造 AnnotationQualityPanel，按 issue code 合并展示重复问题并保留最严重状态
- [x] 5.2 根据 suggested_action 打开对应工作台步骤；没有 action 时保持静态提示兼容
- [x] 5.3 将修复工作台接入 KinematicsWorkflowPage，传入 session video、normalized annotation 和刷新回调
- [x] 5.4 修复保存后刷新 selected annotation、revision、quality、module readiness 和 canSubmit 状态
- [x] 5.5 确保 analysis submit 使用修复后的 annotation revision 和 quality snapshot

## 6. 后端测试

- [x] 6.1 为 scale 换算、零长度、负长度、越界点和非有限坐标增加单元测试
- [x] 6.2 为 waterline 保存和退化线校验增加单元测试
- [x] 6.3 为事件去重、排序、hand_entry 周期质量变化增加单元测试
- [x] 6.4 为 affine/identity mapping confirmed、未确认和无效 stride 增加单元测试
- [x] 6.5 为 repair API 成功、旧 revision 冲突、权限隔离和完整重新验证增加集成测试
- [x] 6.6 验证修复后 quality.source_revision、analysis readiness 和模块 availability 正确更新

## 7. 前端测试与验收

- [x] 7.1 为质量 issue 去重和 suggested action 映射增加组件测试
- [x] 7.2 为画布 CSS 坐标到 intrinsic 视频像素坐标转换增加单元测试
- [x] 7.3 为标尺、水面线、方向、事件和帧映射步骤增加交互测试
- [x] 7.4 为视频加载失败、无视频时禁用画布操作和 409 冲突增加测试
- [x] 7.5 增加端到端验收：上传 CVAT → 出现质量问题 → 打开工作台 → 补充信息 → 重新验证 → 质量面板和模块状态更新
- [x] 7.6 运行 OpenSpec validate、Backend 测试和 Frontend 测试，记录未覆盖的浏览器视频编解码风险
