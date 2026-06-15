# AskBI v2.0 升级实施计划

## Context

AskBI 是一个企业级智能 BI 问数平台，基于 Agno 多智能体框架。当前版本存在以下痛点：
1. **图表引擎局限**：ECharts 仅支持 3 种图表，prompt 极简单（3 行），LLM 生成准确率不高，无交互能力
2. **思考流程薄弱**：终端风格黑色 UI，平面步骤列表，无阶段区分，非实时流式推送
3. **Agent/Skill 硬编码**：6 个 Agent 的 instructions 硬编码在代码中，无可配置界面，无 Skill 系统

本次升级目标：完全替换为 Vega-Lite 图表引擎（10+ 图表类型）；用 SSE 实时推送 + 结构化 Pipeline 视图重构思考流程展示；新增 Skill 技能系统（动态 prompt 注入）和 Agent 管理模块。

**技术决策**：
- 图表引擎：完全替换 ECharts 为 Vega-Lite
- 实时通信：SSE（Server-Sent Events）
- 画布模式：本次不包含
- Skill 编辑器：简易 textarea

---

## 模块总览

| 模块 | 优先级 | 复杂度 | 新增文件 | 修改文件 |
|------|--------|--------|----------|----------|
| A. Skill 技能系统 | P0 | 中 | 4 后端 + 1 前端 | 5 后端 + 3 前端 |
| B. Agent 管理 | P0 | 中 | 2 后端 + 1 前端 | 3 后端 + 2 前端 |
| C. Vega-Lite 替换 | P1 | 中 | 1 前端 | 8 后端 + 4 前端 |
| D. SSE 思考流程 | P1 | 高 | 2 前端 + 1 后端 SSE | 6 后端 + 5 前端 |

### Spec 文件规范

每个模块 4 个 spec 文件，遵循现有格式：

**REQ（需求）**：版本号/状态/优先级 + 需求描述 + 前置条件 + 输入输出 + 处理规则 + 验收标准

**DES-后端**：业务流程 + 业务规则表 + 数据表设计 + 接口设计（请求/响应 JSON 示例）+ 核心类 + 设计约束

**DES-前端**：页面清单 + 页面结构 + 交互流程 + 组件描述 + 接口调用 + 错误处理

**TASK**：任务列表表 + 每个任务的详情（关联需求/技术要点/涉及文件/验收标准）

**CHK**：检查项列表 + 检查步骤 + 预期结果

4 个新模块的 spec 目录：
```
specs/
├── requirement/
│   ├── skill-system/REQ-skill-system.md
│   ├── agent-management/REQ-agent-management.md
│   ├── vega-lite-migration/REQ-vega-lite-migration.md
│   └── sse-thinking-pipeline/REQ-sse-thinking-pipeline.md
├── design/
│   ├── skill-system/{DES-skill-system-前端.md, DES-skill-system-后端.md}
│   ├── agent-management/{DES-agent-management-前端.md, DES-agent-management-后端.md}
│   ├── vega-lite-migration/{DES-vega-lite-migration-前端.md, DES-vega-lite-migration-后端.md}
│   └── sse-thinking-pipeline/{DES-sse-thinking-pipeline-前端.md, DES-sse-thinking-pipeline-后端.md}
├── task/
│   ├── skill-system/TASK-skill-system.md
│   ├── agent-management/TASK-agent-management.md
│   ├── vega-lite-migration/TASK-vega-lite-migration.md
│   └── sse-thinking-pipeline/TASK-sse-thinking-pipeline.md
└── checklist/
    ├── skill-system/CHK-skill-system.md
    ├── agent-management/CHK-agent-management.md
    ├── vega-lite-migration/CHK-vega-lite-migration.md
    └── sse-thinking-pipeline/CHK-sse-thinking-pipeline.md
```

共新建 20 个 spec 文件 + 更新 4 个顶层设计文档。

---

## 模块 A: Skill 技能系统

### A.1 数据库

新建表 `askbi_skills`（在 `askbi_table` schema 下）：

```sql
CREATE TABLE IF NOT EXISTS askbi_table.askbi_skills (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    instructions TEXT NOT NULL,
    category TEXT DEFAULT 'general',  -- general/sql/report/chart/analysis/excel
    is_builtin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    binding_agents JSONB DEFAULT '[]'::jsonb,
    trigger_keywords JSONB DEFAULT '[]'::jsonb,
    priority INTEGER DEFAULT 0,
    scope_type TEXT DEFAULT 'universal',
    scope_datasources JSONB DEFAULT '[]'::jsonb,
    created_by INTEGER REFERENCES askbi_table.askbi_users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

内置 Skill 种子数据（3 条）：SQL 安全规则、报告格式规范、图表生成约束。

### A.2 后端

**新增文件**：
| 文件 | 职责 |
|------|------|
| `backend/skills/__init__.py` | 模块初始化 |
| `backend/skills/skill_manager.py` | Skill CRUD 封装 |
| `backend/skills/skill_registry.py` | 运行时加载 + 60s TTL 缓存 + prompt 拼接 |
| `backend/skills/skill_api.py` | FastAPI 路由 /skills/* |

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/skills` | 列出技能，可选 `?category=` |
| POST | `/skills` | 创建技能 |
| PUT | `/skills/{id}` | 更新技能 |
| DELETE | `/skills/{id}` | 删除（内置不可删） |
| PATCH | `/skills/{id}/toggle` | 启用/禁用 |
| POST | `/skills/{id}/test` | 测试预览注入后的完整 prompt |
| POST | `/skills/ai-create` | AI 辅助生成 instructions |

**Workflow 集成策略**：Prompt 增强，非 Agent 框架迁移。

在 `bi_workflow.py` 和 `askexcel_workflow.py` 中：
- 新增 `_build_system_prompt(agent_name, datasource_name)` 方法
- 从 DB 加载 agent 的 base_instructions（fallback 到硬编码默认值）
- 通过 `skill_registry` 加载匹配的 active skills
- 拼接为：`{base_instructions}\n\n## 附加规则\n{skill_instructions_block}`
- 每个 `_llm()` 调用点传入对应的 `agent_name`

### A.3 前端

**新增**：`frontend/src/components/SkillManager.jsx`
- 左侧：技能列表（表格形式），分类筛选，状态开关
- 右侧：编辑面板 — textarea 编辑器（monospace），绑定智能体多选，触发关键词
- "AI 优化" 按钮：调 LLM 优化 prompt
- 测试面板：选择 agent + 输入问题 → 预览注入后的完整 prompt

---

## 模块 B: Agent 管理

### B.1 数据库

新建表 `askbi_agents`：

```sql
CREATE TABLE IF NOT EXISTS askbi_table.askbi_agents (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT DEFAULT '',
    base_instructions TEXT NOT NULL,
    model_config JSONB DEFAULT '{}'::jsonb,
    bound_skills JSONB DEFAULT '[]'::jsonb,
    tools JSONB DEFAULT '[]'::jsonb,
    is_builtin BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES askbi_table.askbi_users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

启动时从现有 6 个 agent 文件的 INSTRUCTIONS 常量种子数据。

### B.2 后端

**新增文件**：
| 文件 | 职责 |
|------|------|
| `backend/agents_config/__init__.py` | 模块初始化 |
| `backend/agents_config/agent_manager.py` | Agent CRUD 封装 |
| `backend/agents_config/agent_api.py` | FastAPI 路由 /agents/* |

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agents` | 列出所有智能体 |
| POST | `/agents` | 创建自定义智能体 |
| PUT | `/agents/{id}` | 更新配置 |
| DELETE | `/agents/{id}` | 删除（内置不可删） |
| POST | `/agents/{id}/test` | 对话测试 |
| POST | `/agents/{id}/bind-skills` | 绑定/解绑技能 |

### B.3 前端

**新增**：`frontend/src/components/AgentManager.jsx`
- 卡片网格展示所有 Agent
- 编辑面板：textarea 编辑 instructions，model config（模型名/temperature），绑定 skills 多选
- 测试面板：简易对话界面

---

## 模块 C: Vega-Lite 图表引擎替换

### C.1 后端

**重写 `prompt.py`**（当前仅 3 行）：
- `VEGALITE_SYSTEM_PROMPT`：完整的 Vega-Lite 生成指令（schema URL、data 格式、透明背景、色彩调色板、tooltip 规则）
- `CHART_TYPE_SPECS`：10 种图表类型的迷你规范示例（bar/line/pie/area/scatter/heatmap/treemap/stacked_bar/waterfall/radar）
- `build_chart_prompt(question, data, report, chart_type)`：构造最终 prompt

**修改 workflow**：
- `bi_workflow.py`：图表生成步骤使用 `build_chart_prompt()`，system message 改为"Vega-Lite 图表规范生成专家"
- `askexcel_workflow.py`：同上，`_build_chart_prompt()` 重写
- `agents_new/chart_generator.py`、`bi_chart_agent.py`、`askexcel_chart_agent.py`：更新 instructions 文本

### C.2 前端

**修改 `frontend/index.html`**：替换 ECharts CDN 为：
```html
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
```

**新增 `frontend/src/components/VegaChart.jsx`**（~40 行）：
- Props: `spec`（Vega-Lite JSON）
- 使用 `window.vegaEmbed(containerRef, spec, {actions: true})` 渲染
- 自带导出 PNG/SVG 按钮（vega-embed 内置）

**修改 `MessageItem.jsx`**：
- 替换 `import EChart` 为 `import VegaChart`
- 图表验证逻辑：检查 `chart.$schema` 或 `chart.mark`（Vega-Lite），而非 `chart.series`（ECharts）
- 历史消息兼容：旧 ECharts 格式显示"图表引擎已升级"占位

**修改 `ReportManager.jsx`**：替换 EChart 为 VegaChart

**删除 `EChart.jsx`**

### C.3 迁移兼容策略
- 新响应：Vega-Lite JSON，通过 `$schema`/`mark` 字段识别
- 历史消息：ECharts 格式优雅降级（不渲染图表，文字报告不受影响）
- 无需数据库迁移

---

## 模块 D: SSE 实时思考流程 Pipeline

### D.1 SSE 事件格式

```
data: {"stage":"sql_generation","status":"running","message":"第1轮生成SQL...","timestamp":1749408001.456,"duration_ms":1200,"metadata":{"sql":"SELECT..."}}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| stage | string | 阶段ID: understanding/knowledge_retrieval/sql_generation/execution_validation/chart_generation/report_generation/summary |
| status | string | waiting/running/done/error |
| message | string | 可读进度文本 |
| timestamp | float | Unix 时间戳 |
| duration_ms | int/null | 阶段耗时 |
| metadata | object/null | 附加数据（SQL 文本、行数、错误信息等） |

终止事件：`stage: "__done__"` 或 `stage: "__error__"`

### D.2 后端

**重写 `ProgressService`**：
- 新增 `asyncio.Queue` 每个 chatid
- `emit_stage_event(chatid, stage, status, message, metadata)`：推送到 queue + items
- `async stream_events(chatid)`：async generator 从 queue 消费
- 线程安全：用 `loop.call_soon_threadsafe(queue.put_nowait, event)` 从 worker 线程推送
- 保留现有 polling 接口兼容

**修改 workflow**：
- `bi_workflow.py` 新增 `_emit_stage(stage, status, message, metadata)` 方法
- 在每个步骤调用：schema 加载 → understanding, SQL 生成 → sql_generation, 执行 → execution_validation, 报告 → report_generation, 图表 → chart_generation
- `askexcel_workflow.py` 同样模式

**新增 SSE 端点**：
- `GET /progress/stream?chatid=X`（BI）
- `GET /excel/progress/stream?chatid=X`（Excel）
- 使用 `StreamingResponse` + `text/event-stream`
- 保留现有 polling 端点

**修改 `proxy_server.py`**：新增 SSE 代理路由，使用 `httpx` 流式转发

### D.3 前端

**新增 `frontend/src/hooks/useProgressStream.js`**：
- 使用 `fetch()` + `ReadableStream`（非 EventSource，以兼容 Bearer token 认证）
- 返回 `{ connected, stages, lastEvent, error }`
- 断线重连逻辑（2s 延迟，1 次重试）

**新增 `frontend/src/components/ThinkingPipeline.jsx`**：
- Props: `stages`（阶段 map）、`isWaiting`、`open`、`onOpenChange`、`chatType`
- 浅色卡片设计 + 左侧垂直时间线
- 每个阶段：状态图标 + 名称 + 耗时 + 可折叠详情
- SQL 步骤：语法高亮（CSS 关键字着色）
- 错误步骤：红色标记
- 动画过渡：阶段状态变化时平滑过渡

**修改 `MessageItem.jsx`**：
- `isThinking` 时激活 `useProgressStream` hook
- 替换 `<ThinkingProcess>` 为 `<ThinkingPipeline>`
- 历史消息：从 `structuredData.thoughts` 重构已完成的 pipeline

**修改 `StreamingManager.js`**：新增 `progressStages` 字段协调 typing 动画

**修改 `App.jsx`**：`sendMessage` 中 thinkingMsg 添加 `_progressChatId` 字段

### D.4 BI 与 Excel 的阶段定义

| BI 阶段 | 显示名 | Excel 阶段 | 显示名 |
|---------|--------|-----------|--------|
| understanding | 理解问题 | understanding | 理解问题 |
| knowledge_retrieval | 检索知识 | code_generation | 生成代码 |
| sql_generation | 生成SQL | execution_validation | 执行验证 |
| execution_validation | 执行验证 | chart_generation | 生成图表 |
| chart_generation | 生成图表 | report_generation | 生成报告 |
| report_generation | 生成报告 | | |
| summary | 总结回答 | | |

---

## 共享修改文件汇总

| 文件 | A | B | C | D | 改动说明 |
|------|---|---|---|---|---------|
| `config/config_db.py` | x | x | | | 新增 TABLE_SKILLS, TABLE_AGENTS 常量 |
| `utils/db_utils.py` | x | x | | | 新增 DDL + CRUD 方法 + seed 函数 |
| `backend_api_agno.py` | x | x | | | 挂载新路由 + startup 调 seed |
| `bi_workflow.py` | x | | x | x | Skill 注入 + Vega-Lite + stage 事件 |
| `askexcel_workflow.py` | x | | x | x | 同上 |
| `progress_service.py` | | | | x | asyncio.Queue + SSE 支持 |
| `bi_api.py` | | | | x | 新增 SSE 端点 |
| `excel_api.py` | | | | x | 新增 SSE 端点 |
| `prompt.py` | | | x | | 完全重写为 Vega-Lite prompts |
| `chart_generator.py` | | | x | | ECharts → Vega-Lite |
| `bi_chart_agent.py` | | | x | | instructions 更新 |
| `askexcel_chart_agent.py` | | | x | | instructions 更新 |
| `frontend/index.html` | | | x | | CDN 替换 |
| `MessageItem.jsx` | | | x | x | VegaChart + SSE Pipeline |
| `ReportManager.jsx` | | | x | | EChart → VegaChart |
| `Sidebar.jsx` | x | x | | | 新增导航入口 |
| `App.jsx` | x | x | | x | 新组件路由 + SSE 生命周期 |
| `api.js` | x | x | | x | 新增 API 方法 |
| `proxy_server.py` | | | | x | SSE 代理路由 |
| `StreamingManager.js` | | | | x | 阶段协调 |

---

## 实施顺序

```
Phase 0: 创建 Spec 文件（遵循现有 REQ/DES/TASK/CHK 格式）
  ├─ 0.1 新建 specs/requirement/skill-system/REQ-skill-system.md
  ├─ 0.2 新建 specs/design/skill-system/DES-skill-system-后端.md
  ├─ 0.3 新建 specs/design/skill-system/DES-skill-system-前端.md
  ├─ 0.4 新建 specs/task/skill-system/TASK-skill-system.md
  ├─ 0.5 新建 specs/checklist/skill-system/CHK-skill-system.md
  ├─ 0.6 同上 4 套文件 for agent-management
  ├─ 0.7 同上 4 套文件 for vega-lite-migration
  ├─ 0.8 同上 4 套文件 for sse-thinking-pipeline
  ├─ 0.9 更新 specs/design/01-architecture.md（新增模块描述）
  ├─ 0.10 更新 specs/design/02-data-model.md（新增表定义）
  ├─ 0.11 更新 specs/design/03-ui-ux.md（新增组件/页面描述）
  ├─ 0.12 更新 specs/design/04-api-contract.md（新增 API 清单）
  └─ 0.13 用户审核所有 spec 文件 → 确认无误后进入 Phase 1

Phase 1: 数据层 + 后端基础 (A+B)
  ├─ 1.1 config_db.py 新增常量
  ├─ 1.2 db_utils.py 新增 DDL + CRUD + seed
  ├─ 1.3 skill_manager.py + skill_registry.py
  ├─ 1.4 agent_manager.py
  ├─ 1.5 skill_api.py + agent_api.py
  ├─ 1.6 backend_api_agno.py 挂载路由
  └─ 1.7 验证：启动后端，curl 测试 CRUD API

Phase 2: Workflow 集成 (A+B)
  ├─ 2.1 bi_workflow.py 添加 _build_system_prompt + Skill/Agent 加载
  ├─ 2.2 askexcel_workflow.py 同上
  └─ 2.3 验证：发送 BI/Excel 问题，确认 Skill 注入生效

Phase 3: Vega-Lite 后端 (C)
  ├─ 3.1 重写 prompt.py
  ├─ 3.2 修改 bi_workflow.py 图表生成
  ├─ 3.3 修改 askexcel_workflow.py 图表生成
  ├─ 3.4 更新 agent instructions 文件
  └─ 3.5 验证：发送问题，确认返回 Vega-Lite JSON

Phase 4: Vega-Lite 前端 (C)
  ├─ 4.1 index.html CDN 替换
  ├─ 4.2 新建 VegaChart.jsx
  ├─ 4.3 修改 MessageItem.jsx
  ├─ 4.4 修改 ReportManager.jsx
  ├─ 4.5 删除 EChart.jsx
  └─ 4.6 验证：端到端问答 → 图表渲染

Phase 5: SSE 后端 (D)
  ├─ 5.1 重写 ProgressService（asyncio.Queue）
  ├─ 5.2 bi_workflow.py 添加 _emit_stage()
  ├─ 5.3 askexcel_workflow.py 添加 _emit_stage()
  ├─ 5.4 新增 SSE 端点
  ├─ 5.5 proxy_server.py 添加 SSE 代理
  └─ 5.6 验证：curl SSE 端点，确认事件流

Phase 6: SSE 前端 (D)
  ├─ 6.1 新建 useProgressStream.js
  ├─ 6.2 新建 ThinkingPipeline.jsx
  ├─ 6.3 修改 MessageItem.jsx 集成 SSE + Pipeline
  ├─ 6.4 修改 StreamingManager.js
  ├─ 6.5 修改 App.jsx
  └─ 6.6 验证：实时 Pipeline 可视化

Phase 7: Skill/Agent 前端 (A+B)
  ├─ 7.1 新建 SkillManager.jsx
  ├─ 7.2 新建 AgentManager.jsx
  ├─ 7.3 修改 Sidebar.jsx 导航
  ├─ 7.4 修改 App.jsx 路由
  ├─ 7.5 api.js 新增方法
  └─ 7.6 验证：完整 CRUD + 测试面板
```

---

## 验证方案

### 后端验证
1. **启动后端**：`conda activate agent-framework && python backend_api_agno.py`
2. **Skill CRUD**：`curl -X GET http://localhost:8002/skills -H "Authorization: Bearer {token}"`
3. **Agent CRUD**：`curl -X GET http://localhost:8002/agents -H "Authorization: Bearer {token}"`
4. **Skill 注入**：创建 Skill → 发送 BI 问题 → 检查日志中 system prompt 是否包含 Skill 内容
5. **Vega-Lite**：发送问题 → 检查 response.chart 是否包含 `$schema` 和 `mark` 字段
6. **SSE**：`curl -N http://localhost:8002/progress/stream?chatid={id}` → 确认收到 event stream

### 前端验证
1. **启动前端**：`cd frontend && npm run dev`
2. **Skill 管理**：侧边栏导航 → 技能管理 → 新建/编辑/删除/启用禁用
3. **Agent 管理**：侧边栏导航 → 智能体管理 → 查看/编辑/测试
4. **图表渲染**：发送 BI 问题 → 确认 Vega-Lite 图表正确渲染 + 导出按钮可用
5. **Pipeline 展示**：发送问题 → 实时观察阶段卡片从 waiting → running → done 变化
6. **历史消息**：切换到旧会话 → 确认历史消息正常显示（图表优雅降级）

### 端到端验证
1. 创建新 Skill（SQL 安全规则）→ 绑定到 bi_sql_agent → 发送 BI 问题 → 验证 SQL 遵循规则
2. 修改 Agent 的 model_config → 发送问题 → 验证使用了指定模型
3. 发送 Excel 问题 → 验证 Pipeline 显示 Excel 特定阶段
4. 检查旧消息 → 验证 ECharts 图表优雅降级为占位提示
