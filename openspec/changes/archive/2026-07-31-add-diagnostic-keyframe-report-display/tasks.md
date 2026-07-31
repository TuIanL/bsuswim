## 1. 后端关键帧展示语义

- [x] 1.1 建立关键帧 presentation registry，为身体轴、肘角、膝角、手臂伸展和头部运动关键帧提供中文标题、指标标签、单位、极值含义和事实性说明。
- [x] 1.2 扩展 artifact manifest 和 `ReportAsset` 投影，保留 presentation metadata、指标数值、选择侧别、annotation frame、source video frame 和 source annotation revision。
- [x] 1.3 检查页面资产排序和跨侧关键帧选择，确保页面 2、3、4 只接收对应 source module keys，并在图表前稳定放置代表性关键帧。
- [x] 1.4 为关键帧缺失、指标不可用、帧映射未确认和视频解码失败补充模块级质量说明，确保报告仍可生成。

## 2. 关键帧图片渲染

- [x] 2.1 检查 annotated keyframe renderer 的标题、数值和 caption 绘制路径，统一使用可用中文字体和可靠 fallback。
- [x] 2.2 更新关键帧图片文案，移除原始 artifact key 直接作为用户标题的情况，并确保不生成问号替代字形或动作阶段断言。
- [x] 2.3 增加渲染器测试，验证中文标题、指标单位、骨架叠加、事实性说明和无值状态的输出。

## 3. 前端报告数据和组件

- [x] 3.1 扩展 `ReportAsset` 与 `normalizeReportData`，兼容读取关键帧的 presentation、模块、指标和帧定位字段，同时保持旧报告数据可渲染。
- [x] 3.2 实现关键帧证据卡片或证据带，展示图片、诊断含义、指标值/单位、annotation frame 和 source video frame。
- [x] 3.3 调整页面 2、3、4 的资产布局，使关键帧位于对应模块的证据区域，并对无关键帧和 partial 状态显示质量说明。
- [x] 3.4 确保普通图表资产继续使用现有渲染路径，关键帧组件不改变 legacy report 的展示行为。

## 4. 打印与 PDF 布局

- [x] 4.1 将关键帧证据布局接入现有 print route，保持五个 `print-page` 和原有 page number/page type 语义。
- [x] 4.2 为关键帧图片、标题和元数据设置稳定尺寸与分页规则，避免卡片跨页、文字溢出或图片被截断。
- [x] 4.3 使用同一份 ReportData 验证 Web 和 print route 的关键帧 key、顺序、标题、数值和 source revision 一致。

## 5. 测试与验收

- [x] 5.1 增加后端报告资产投影测试，验证关键帧元数据完整、模块归属正确、缺失资产可降级。
- [x] 5.2 增加前端归一化和组件测试，验证关键帧卡片内容、旧数据兼容和页面模块过滤。
- [x] 5.3 更新报告契约测试，验证五页结构不变、页面 2 至 4 包含预期关键帧、页面 5 不新增动作阶段结论。
- [x] 5.4 补充 print route 五页结构、关键帧可加载语义和布局回归测试，并复用现有 PDF 五页/语义标记协议。
- [x] 5.5 使用现有真实或 golden fixture 完成一次端到端验收，确认指标、关键帧资产、报告 HTML 和 PDF 的 source revision 一致。
