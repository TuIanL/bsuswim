## 1. 仓库审计

- [x] 1.1 使用 `git ls-files frontend` 记录旧 Next.js 前端的全部 tracked files（31 files）
- [x] 1.2 检查 `frontend/package.json`、package-lock、Next config、Tailwind config 和源码目录
- [x] 1.3 记录旧前端两套 route 的内容：
  - `/`：营销 landing page（Navbar、Hero、Features、Specs、AnalysisOutputs、FAQ、CTA、Footer 等）
  - `/platform`：React Demo SPA（upload、tasks、job、workspace、report、training 视图）
- [x] 1.4 对照 `frontend-vue` 标记每项功能为：superseded / demo-only / intentionally retired / missing-and-required
- [x] 1.5 未发现 `missing-and-required` 项，继续删除
- [x] 1.6 搜索活动代码和文档中的旧路径引用：`frontend/`、`Next.js`、`next dev`、`next build`、`next start`
- [x] 1.7 检查 `.github/workflows/`、Docker、部署脚本、启动脚本和环境变量中是否存在旧前端引用（无 CI workflows）
- [x] 1.8 确认 `docker-compose.yml` 没有依赖旧前端
- [x] 1.9 确认 `start-web.command` 已使用 `frontend-vue`

## 2. OpenSpec capability 更新

- [x] 2.1 创建 `official-web-frontend-boundary` 的 ADDED delta spec
- [x] 2.2 修改 `swim-analysis-platform-navigation` 的 MODIFIED delta spec
- [x] 2.3 创建 `zhiyong-yunshu-landing-page` 的 REMOVED delta spec
- [x] 2.4 确认三个 delta spec 内容完成且与 proposal/design 一致
- [x] 2.5 移除对旧 marketing homepage 的导航要求，定义应用根入口行为
- [x] 2.6 移除品牌控制（brand control）点击行为的规格场景
- [x] 2.7 确认归档 change 文件保持不变
- [x] 2.8 验证 OpenSpec CLI 对全 REMOVED delta 的处理行为（validation 通过）
- [x] 2.9 执行 `openspec validate remove-obsolete-next-frontend --strict`

## 3. 删除旧前端

- [x] 3.1 删除 `frontend/` 下的全部 tracked files
- [x] 3.2 删除旧 `package.json` 和 `package-lock.json`
- [x] 3.3 删除 Next.js 配置（`next.config.mjs`、`next-env.d.ts`）
- [x] 3.4 删除 React 组件和页面（`app/`、`components/`、`lib/`）
- [x] 3.5 删除旧 Tailwind/PostCSS 配置（`tailwind.config.ts`、`postcss.config.mjs`）
- [x] 3.6 删除旧 ESLint 配置（`.eslintrc.json`）
- [x] 3.7 删除旧 TypeScript 配置（`tsconfig.json`）
- [x] 3.8 不创建 `legacy/`、`archive/` 或 `examples/` 代码副本
- [x] 3.9 确认 `git status` 中旧前端全部表现为删除，不出现移动后的副本

## 4. 清理忽略规则

- [x] 4.1 从 `.gitignore` 删除 `frontend/node_modules/`
- [x] 4.2 从 `.gitignore` 删除 `frontend/.next/`
- [x] 4.3 从 `.gitignore` 删除 `frontend/out/`
- [x] 4.4 从 `.gitignore` 删除 `frontend/.env*.local`
- [x] 4.5 保留所有 `frontend-vue/` 忽略规则
- [x] 4.6 确认没有为旧前端新增意外的通用忽略规则

## 5. 后端 CORS 默认配置清理

- [x] 5.1 从 `backend/app/core/config.py` 的默认 `cors_origins` 中删除 `"http://localhost:3000"`
- [x] 5.2 从 `backend/app/core/config.py` 的默认 `cors_origins` 中删除 `"http://127.0.0.1:3000"`
- [x] 5.3 确认两个 port 5173 的 Vue origin 保留
- [x] 5.4 确认环境变量覆盖能力保持不变
- [x] 5.5 添加 settings 测试：`backend/tests/test_settings.py`（默认 origins 包含 5173、不包含 3000）

## 6. README 更新

- [x] 6.1 从仓库结构中删除 `frontend/`
- [x] 6.2 将 `frontend-vue/` 描述为"正式且唯一的 Vue 3 Web 分析平台"
- [x] 6.3 确认启动说明只包含 Vue/Vite，不含 Next.js
- [x] 6.4 删除任何 Next.js 或 React 启动说明
- [x] 6.5 将文档导航中的本机绝对路径改为仓库相对路径
- [x] 6.6 增加旧前端已退休的简短迁移说明
- [x] 6.7 提醒已有 clone 在残留目录存在时执行 `rm -rf frontend`

## 7. Maintained docs 更新

- [x] 7.1 更新 `docs/local-development.md`：删除"保留 frontend/ 作为交互参考"的说明
- [x] 7.2 明确所有 Web 命令从 `frontend-vue/` 执行
- [x] 7.3 更新 `docs/tech-stack.md`：从当前实现状态中删除旧 Next.js 前端
- [x] 7.4 明确 Vue 3 + Vite 是唯一支持的 Web 栈
- [x] 7.5 搜索其他 maintained docs 中的旧前端引用（更新 `.workbuddy/memory/2026-07-06.md`）
- [x] 7.6 不修改 `openspec/changes/archive/` 中的历史文档

## 8. 自动化与脚本确认

- [x] 8.1 验证 `start-web.command` 使用 `frontend-vue`
- [x] 8.2 验证 `stop-web.command` 不依赖旧 Next.js 进程名或目录
- [x] 8.3 检查 CI 是否存在 `cd frontend`（无 CI 配置）
- [x] 8.4 检查部署配置是否存在 `.next`、`next start` 或旧前端端口
- [x] 8.5 检查后端 CORS 配置是否存在只服务于旧 Next.js 的 origin（已在任务 5 处理）
- [x] 8.6 若没有旧引用，不为本 Change 创建无意义的配置修改

## 9. Vue 构建验证

- [x] 9.1 `node_modules` 已存在，`npm ci` 可执行
- [x] 9.2 执行 `npm run build`（`vue-tsc --noEmit` + Vite 打包均通过）
- [x] 9.3 Vite production bundle 成功生成（`dist/` 目录存在）
- [x] 9.4 启动 Vue dev server 并检查根路径（手动验证）
  - 手动验证通过：`http://127.0.0.1:5174/` → 自动重定向到 `/athletes`
- [x] 9.5 检查未登录 API 模式跳转到 `/login`（手动验证）
  - 手动验证通过：`http://127.0.0.1:5175/`（VITE_API_BASE_URL 已设置）→ 跳转到 `/login`
- [x] 9.6 检查 demo 模式可进入 `/athletes`（手动验证）
  - 手动验证通过：demo 模式 `http://127.0.0.1:5174/` → 直接进入 `/athletes`，侧边栏可见

## 10. 后端回归

- [x] 10.1 执行后端测试套件（137 passed, 2 pre-existing failures in `test_side_view_metrics.py` 和 `test_normalized_annotation.py`）
- [x] 10.2 确认静态文件或模板测试不依赖 `frontend/`
- [x] 10.3 CORS settings 测试通过（`test_settings.py` 2/2 passed）

## 11. Release gate

- [x] 11.1 `git ls-files frontend` 返回空（0 files）
- [x] 11.2 本地 `frontend/` 目录残留由 migration note 处理（`rm -rf frontend`）
- [x] 11.3 `test -f frontend-vue/package.json` 通过
- [x] 11.4 活动代码中不存在 `next dev`、`next build` 或 `next start`
- [x] 11.5 活动文档中不存在"保留旧 frontend 作为参考"
- [x] 11.6 `.gitignore` 中不存在旧 Next.js 路径
- [x] 11.7 后端默认 CORS origins 中不包含 3000 端口
- [x] 11.8 现行 specs 中不包含导航到已退休营销 surface 的要求
- [x] 11.9 旧前端引用只存在于：`openspec/changes/archive/`、当前 Change artifacts、README 迁移说明
- [x] 11.10 OpenSpec strict validation 通过
- [x] 11.11 Vue production build 通过
- [x] 11.12 后端测试套件通过（137 passed, 2 pre-existing failures）
