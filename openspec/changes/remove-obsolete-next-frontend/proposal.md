## Why

仓库当前同时保留两个独立 Web 应用：

- `frontend/`：早期 Next.js 14 + React 18 原型，包含两条耦合的 route：
  - `/`：品牌营销 landing page（Hero、Features、FAQ 等）；
  - `/platform`：基于 localStorage demo data 的自包含 React 演示 SPA（upload、tasks、workspace、report、training 视图）。
- `frontend-vue/`：当前正式维护的 Vue 3 + Vite 业务平台，已承载认证、运动员管理、测试任务、多机位上传、工作台、报告和 PDF 打印。

旧 Next.js 前端已经不再维护，但仍然存在于仓库根目录、依赖锁文件、`.gitignore`、默认后端 CORS 配置、开发文档和现行 OpenSpec capability 中。两条 route 互相链接，共同构成一个已退休的产品原型。

这会造成的具体问题：

1. 新开发者无法确定应该启动或修改哪套前端；
2. 依赖扫描、代码搜索和自动化工具会把两套前端都识别为活动工程；
3. React/Next.js 和 Vue/Vite 两套依赖需要被重复维护；
4. 旧 Demo 流程可能被误认为真实业务入口；
5. 后端默认 CORS 配置仍允许旧 Next.js 的 3000 端口，暗示该端口仍是受支持客户端；
6. `swim-analysis-platform-navigation` 规格依赖营销首页作为"返回首页"目标，两者存在运行时耦合；
7. OpenSpec 仍要求提供 `zhiyong-yunshu-landing-page` 能力，但其实现已不属于当前产品范围。

因此，需要正式退休旧 Next.js 应用，并将 `frontend-vue/` 固化为仓库中唯一的正式 Web 应用。

## What Changes

- 删除整个 `frontend/` 目录，包括 Next.js 14 配置、React 组件、Tailwind 配置、package.json 和 package-lock.json。
- 将 `frontend-vue/` 定义为仓库唯一正式 Web 前端和唯一 Web 构建目标。
- 删除 `.gitignore` 中只服务于旧 Next.js 前端的规则。
- 从后端默认 CORS origins 中移除旧 Next.js 的 3000 端口。
- 更新 README、技术栈说明、本地开发说明和相关文档。
- 修正 README 中指向开发者本机绝对路径的文档链接。
- 新增 `official-web-frontend-boundary` capability，定义唯一前端边界。
- 修改 `swim-analysis-platform-navigation` capability，移除对旧营销首页的依赖。
- 退休 `zhiyong-yunshu-landing-page` capability。
- 保留历史 OpenSpec archive 记录，不重写已归档的设计记录。
- 增加删除后的仓库检查和 Vue 生产构建验证。

## Capabilities

### New Capabilities

- `official-web-frontend-boundary`
  - 定义 `frontend-vue/` 为唯一正式 Web 应用
  - 定义正式开发、构建和部署命令
  - 禁止活动文档和自动化入口重新引用已删除的 `frontend/`
  - 活跃仓库中不得存在第二套 Tracked Web 应用

### Modified Capabilities

- `swim-analysis-platform-navigation`
  - 平台入口完全由 Vue Router 提供
  - 根路径进入 Vue 业务平台入口
  - 不再要求保留或链接旧 Next.js 营销首页
  - 不再将品牌 Logo 点击行为定义为"返回首页 surface"
  - 应用程序根入口独立于任何营销前端

### Removed Capabilities

- `zhiyong-yunshu-landing-page`
  - 退休独立的 Next.js 单页营销网站。
  - 后续如重新需要公开产品官网，应通过独立 Vue 应用或独立站点 Change 重新立项。

### Implementation Retirement

- 删除 `/platform` React Demo SPA 及其 localStorage 数据层。
- 其所演示的分析任务、工作台和报告能力不被移除；这些能力已经由正式 Vue 平台承接，对应 capability 保持不变。

## Impact

### Deleted

- `frontend/`
  - Next.js 营销 route（`/`）
  - React 演示平台 route（`/platform`）
  - React 组件和 localStorage 数据层
  - Next.js、React、Tailwind 依赖
  - 两条 route 之间的品牌与导航链接

### Modified

- `.gitignore`
- `README.md`
- `docs/local-development.md`
- `docs/tech-stack.md`
- `backend/app/core/config.py`
  - 删除旧 Next.js 前端默认 CORS origins（3000 端口）
  - 保留 Vue 开发 origins（5173 端口）
  - 保留环境变量覆盖能力
- `openspec/specs/swim-analysis-platform-navigation`
- `openspec/specs/zhiyong-yunshu-landing-page`

### Verified, Normally Unchanged

- `frontend-vue/`
- `start-web.command`
- `stop-web.command`
- `docker-compose.yml`
- 后端 route 路径和请求/响应 contract
- 认证行为
- 数据库模型和 migration
- 模型服务集成
- 报告生成行为
- PDF 导出行为

### Not Affected

- API request 和 response contracts
- 数据库 schema
- 认证逻辑
- 分析流程
- 报告数据结构
- PDF 导出行为
- 归档 OpenSpec change 中的历史记录

## Breaking Changes

- `frontend/` 不再存在，不能继续执行 `cd frontend && npm run dev`。
- 旧 Next.js landing page 和基于 localStorage 的 React Demo 不再作为活动产品入口。
- 已有本地 clone 中被 Git 忽略的 `frontend/node_modules` 或 `frontend/.next` 可能需要开发者手动删除。
- 后端默认 CORS 配置不再包含 3000 端口，开发旧前端的自定义部署需通过环境变量额外配置。
