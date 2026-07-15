## Context

当前仓库中存在两套 Web 应用：

| 路径 | 技术栈 | 当前定位 |
|---|---|---|
| `frontend/` | Next.js 14、React 18、Tailwind | 两条耦合 route：营销 landing page（`/`）+ React Demo SPA（`/platform`） |
| `frontend-vue/` | Vue 3、Vite、Element Plus、Pinia、ECharts | 正式业务平台 |

旧 React 前端包含两个互相链接的表面：

```text
frontend/
├── /                → 营销单页（Navbar → Hero → Features → Specs → FAQ → Footer）
└── /platform        → Demo SPA（upload → tasks → job → workspace → report → training）
    └── 依赖 localStorage demo data，无真实后端连接
```

正式 Vue 平台已经覆盖：登录注册、运动员管理、测试任务、多机位上传、分析任务、可视化工作台、结构报告、PDF 打印。

后端 CORS 配置仍包含旧 Next.js 的 3000 端口作为默认 origin。

## Goals / Non-Goals

**Goals:**

- 仓库中只保留一个正式 Web 应用
- 开发者只能从文档和启动脚本得到 `frontend-vue/` 这一条路径
- 删除旧 Next.js 代码和依赖（含营销 route 和 Demo SPA）
- 从后端默认 CORS origins 中移除已退休前端的 3000 端口
- 保证删除后 Vue 构建和现有业务流程不受影响
- 使现行 OpenSpec capabilities 与真实代码一致
- `swim-analysis-platform-navigation` 不再依赖已删除的营销首页
- `zhiyong-yunshu-landing-page` 被明确退休而非默默忽略
- 保留历史设计记录和 Git 历史可追溯性

**Non-Goals:**

- 不把 `frontend-vue/` 重命名为 `frontend/`
- 不将旧 Next.js landing page 或 Demo SPA 迁移到 Vue
- 不迁移旧 React Demo 中的组件或样式
- 不在本 Change 中新增 Vue 品牌 Logo 点击行为
- 不改后端 API route 路径和 request/response contracts
- 不修改数据库 schema 和 migration
- 不修改模型服务集成
- 不修改报告生成和 PDF 导出行为
- 不建立新的 monorepo、workspace 或根级 package.json
- 不删除归档 OpenSpec 中关于旧 Next.js 前端的历史记录
- 不移除或限制 CORS 环境变量覆盖能力，本 Change 只清理默认值

## Decisions

### Decision 1: Delete the old frontend instead of moving it to an archive directory

`frontend/` SHALL be removed from the active working tree.

It SHALL NOT be moved to:

```text
archive/frontend/
legacy/frontend/
examples/frontend/
```

Rationale:

1. Git history already preserves the complete implementation
2. Moving to another repository directory would still expose it to dependency scanning
3. Code search and AI coding tools would continue to treat it as relevant code
4. An archive directory creates continued ambiguity about which application is supported
5. Retaining package manifests would continue to trigger dependency update notifications
6. The goal is to eliminate ambiguity, not to rename it

### Decision 2: Keep the canonical path as `frontend-vue/`

This Change SHALL NOT rename `frontend-vue/` to `frontend/`.

Rationale:

- Current documentation, scripts and deployment assumptions already use `frontend-vue/`
- Renaming would create a large path-only diff
- Active OpenSpec changes and implementation references already point to `frontend-vue/`
- A future repository-layout cleanup can handle naming separately

### Decision 3: Retire rather than silently ignore the landing-page capability

The canonical `zhiyong-yunshu-landing-page` specification currently requires a responsive single-page marketing site.

Deleting `frontend/` while retaining this canonical capability would make the repository non-compliant with its own specifications.

Therefore this Change SHALL explicitly remove the capability.

The historical archived change SHALL remain unchanged.

### Decision 4: Do not migrate old-only features inside this Change

Before deletion, old frontend features SHALL be classified as:

| Classification                        | Handling                                               |
| ------------------------------------- | ------------------------------------------------------ |
| Already available in Vue              | Delete old duplicate                                   |
| Demo-only and no longer authoritative | Retire                                                 |
| Marketing-only landing page           | Retire capability                                      |
| Potential future value                | Record in audit, do not migrate                        |
| Required but missing from Vue         | Block deletion and open a separate prerequisite Change |

### Decision 5: Archived OpenSpec records are immutable historical records

References to `frontend/`, Next.js or React inside `openspec/changes/archive/` SHALL NOT be rewritten. They describe what was true when those changes were implemented.

Only current canonical specs, active changes, README and maintained documentation are subject to cleanup.

### Decision 6: Remove obsolete default CORS origins without changing API contracts

The default CORS configuration currently includes port 3000 origins that served the retired Next.js application.

This Change SHALL remove:

- `http://localhost:3000`
- `http://127.0.0.1:3000`

It SHALL preserve:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

This is treated as repository-boundary and security-configuration cleanup rather than an API contract change.

Environment-based configuration MAY still provide additional origins for an explicit deployment.

### Decision 7: Root navigation belongs to the Vue application, not a marketing page

The Vue router remains the Web entry point. The application root (`/`) SHALL resolve into the maintained business platform.

Current root behavior is:

```text
/  →  /athletes (authenticated)
/  →  /login (unauthenticated, API mode)
```

The system SHALL NOT maintain a second root application solely to display a marketing page.

### Decision 8: Brand control click behavior is not part of this Change

The Vue `App.vue` brand area currently has no click handler or `router-link`. Adding "click brand to return to app root" is a separate UX concern.

This Change SHALL NOT add that behavior. Specification scenarios that require brand control navigation shall be removed or replaced, not implemented.

### Decision 9: No backend or model-service cleanup beyond CORS defaults

This Change affects repository frontend ownership and its boundary traces only.

It SHALL NOT:

- Change backend route paths or request/response contracts
- Change authentication behavior
- Change database models or migrations
- Change model-service integration
- Change report schemas or PDF export behavior

The only backend runtime source file modified by this Change is `backend/app/core/config.py` for CORS default origins.

Backend test files MAY be modified to verify the new default CORS origins.

### Decision 10: Local ignored artifacts require an explicit migration note

After tracked `frontend/` files are deleted, existing developer machines may still contain:

```text
frontend/node_modules/
frontend/.next/
frontend/out/
frontend/.env.local
```

Git does not remove ignored files automatically.

The migration note SHALL instruct developers to run `rm -rf frontend` after pulling the change if the directory remains locally.

### Decision 11: Startup scripts and Docker are verified, not modified

`start-web.command` already targets `frontend-vue/`. `docker-compose.yml` already has no frontend service. These files are verified for correctness but not modified unless verification finds an actual obsolete reference.

## Specification Strategy

This Change creates one capability, modifies one capability, and removes one capability:

```text
official-web-frontend-boundary       ADDED
swim-analysis-platform-navigation   MODIFIED
zhiyong-yunshu-landing-page         REMOVED
```

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|---|---|---|
| 开发者 clone 后本地残留 `frontend/` 目录（Git-ignored） | High | Migration note 明确要求删除 |
| 自定义部署依赖 port 3000 CORS 项 | Low | 保留环境变量覆盖，不禁止显式配置 |
| 后端测试中某个 fixture 或 tooling 依赖旧前端 | Low | Verification 步骤包含 `pytest` 全量运行 |
| 未来需要营销官网时需重新立项 | Medium | 明确记录在 retired capability 中和 proposal 中 |
| 品牌 Logo 不可点击的体验差异 | Low | 标记为未来独立 Change，不混入本 Change |

## Migration Note for Developers

```bash
# After pulling this change, if frontend/ directory still exists locally:
rm -rf frontend

# Verify the change:
test ! -e frontend           # 旧目录已删除
test -f frontend-vue/package.json  # Vue 前端存在
```
