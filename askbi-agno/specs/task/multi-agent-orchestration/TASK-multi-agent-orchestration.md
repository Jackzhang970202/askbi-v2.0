# 任务清单

**版本**: v2.2
**模块**: 多智能体编排 (multi-agent-orchestration)
**关联需求**: REQ-multi-agent-orchestration

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-multi-agent-orchestration-会话模型-001 | [后端] 扩展统一会话上下文字段与读写接口 | REQ-multi-agent-orchestration-统一会话模型 | P0 | 已完成 |
| TASK-multi-agent-orchestration-普通对话-002 | [后端] 实现普通对话智能体与接口 | REQ-multi-agent-orchestration-普通对话链路 | P0 | 已完成 |
| TASK-multi-agent-orchestration-上下文挂载-003 | [后端] 实现会话上下文挂载与切换 API | REQ-multi-agent-orchestration-会话内上下文挂载 | P0 | 已完成 |
| TASK-multi-agent-orchestration-发送路由-004 | [前后端] 按会话上下文重构消息路由与 SSE | REQ-multi-agent-orchestration-消息路由与历史恢复 | P0 | 已完成 |
| TASK-multi-agent-orchestration-前端交互-005 | [前端] 重构新建对话、输入框加号和历史展示 | REQ-multi-agent-orchestration-统一会话模型 | P0 | 已完成 |
| TASK-multi-agent-orchestration-团队整合-006 | [前后端] 将团队能力接入统一会话模型 | REQ-multi-agent-orchestration-会话内上下文挂载 | P0 | 已完成 |
| TASK-multi-agent-orchestration-验证同步-007 | [验证] 运行接口/UI 验证并同步 spec 状态 | REQ-multi-agent-orchestration-消息路由与历史恢复 | P0 | 未开始 |
| TASK-multi-agent-orchestration-图表卡片-008 | [前端] 重构图表结果卡片与详情面板层级 | REQ-multi-agent-orchestration-图表分析体验 | P1 | 未开始 |
| TASK-multi-agent-orchestration-图表视觉-009 | [前端] 统一图表主题色板与弱化辅助元素 | REQ-multi-agent-orchestration-图表分析体验 | P1 | 未开始 |
| TASK-multi-agent-orchestration-图表验证-010 | [验证] 校验图表卡片态、详情态与视觉一致性 | REQ-multi-agent-orchestration-图表分析体验 | P1 | 未开始 |

---

## 任务详情

### TASK-multi-agent-orchestration-会话模型-001 [后端] 扩展统一会话上下文字段与读写接口

**关联需求**: REQ-multi-agent-orchestration-统一会话模型
**描述**: 扩展会话表与服务层，支持 `context_type`、`context_ref_id`、`context_ref_name` 等字段，能够表示普通对话、BI、Excel、Team 四种会话上下文。
**技术要点**: 兼容现有 askbi_chat_session；历史数据可回填默认 `general`；读写接口统一封装在 session_service/db_utils
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `utils/db_utils.py`
- `backend/ask/services/session_service.py`
- `config/config_db.py`

**验收标准**:
- [ ] 会话可持久化上下文类型和引用信息
- [ ] 老会话无上下文字段时可按 `general` 读取
- [ ] 历史查询接口可返回上下文信息

---

### TASK-multi-agent-orchestration-普通对话-002 [后端] 实现普通对话智能体与接口

**关联需求**: REQ-multi-agent-orchestration-普通对话链路
**描述**: 新增普通对话智能体配置与普通对话 ask 接口，支持未绑定上下文时的消息处理和持久化。
**技术要点**: 可复用 agent_manager；需要独立 API 路由；普通对话不依赖 datasource_name
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/agents_config/agent_manager.py`
- `backend/ask/api/bi_api.py` 或新增通用 chat API
- `backend_api_agno.py`

**验收标准**:
- [ ] 未绑定上下文时可收到普通对话回复
- [ ] 普通对话消息正常写入历史
- [ ] 普通对话不触发问数工作流

---

### TASK-multi-agent-orchestration-上下文挂载-003 [后端] 实现会话上下文挂载与切换 API

**关联需求**: REQ-multi-agent-orchestration-会话内上下文挂载
**描述**: 为现有会话新增挂载数据源、Excel 数据源、团队与清除上下文的接口。
**技术要点**: 输入校验；team/datasource 存在性校验；切换后仅影响后续消息
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/bi_api.py`
- `backend/ask/api/excel_api.py`
- `backend/ask/api/team_api.py`
- `backend/ask/services/session_service.py`

**验收标准**:
- [ ] 能给指定 chat_id 绑定数据库数据源
- [ ] 能给指定 chat_id 绑定 Excel 数据源
- [ ] 能给指定 chat_id 绑定团队
- [ ] 能清除会话上下文并退回普通对话

---

### TASK-multi-agent-orchestration-发送路由-004 [前后端] 按会话上下文重构消息路由与 SSE

**关联需求**: REQ-multi-agent-orchestration-消息路由与历史恢复
**描述**: 改造发送消息与流式进度逻辑，按会话上下文而非 activeTab 选择 general / bi / excel / team 链路。
**技术要点**: App.jsx `sendMessage` 重构；SSE 路径动态选择；历史恢复同步上下文
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/App.jsx`
- `frontend/src/hooks/useProgressStream.js`
- `frontend/src/services/api.js`

**验收标准**:
- [ ] 发送路由不再依赖 activeTab
- [ ] SSE 路径与当前上下文匹配
- [ ] 恢复历史会话后发送消息仍走正确链路

---

### TASK-multi-agent-orchestration-前端交互-005 [前端] 重构新建对话、输入框加号和历史展示

**关联需求**: REQ-multi-agent-orchestration-统一会话模型
**描述**: 新建对话改为直接进入普通对话；在输入区加入上下文挂载菜单；统一历史展示上下文标签。
**技术要点**: UI 尽量复用现有组件；减少对 Sidebar 结构的破坏性改动；支持上下文清除展示
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/App.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/components/SkillSelector.jsx`

**验收标准**:
- [ ] 新建对话进入普通会话
- [ ] 输入区存在加号并可挂载上下文
- [ ] 历史列表可区分普通/BI/Excel/Team 会话
- [ ] 团队会话不再混入 BI 语义展示

---

### TASK-multi-agent-orchestration-团队整合-006 [前后端] 将团队能力接入统一会话模型

**关联需求**: REQ-multi-agent-orchestration-会话内上下文挂载
**描述**: 调整团队入口与历史恢复逻辑，使团队成为统一会话的一种上下文，而非新建页上的独立模式入口。
**技术要点**: Team chat 元数据回写；会话恢复时同步 teamId/teamName；保留 TeamCoordinator 现有执行能力
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`
- `backend/ask/api/team_api.py`
- `backend/ask/team_engine/coordinator.py`

**验收标准**:
- [ ] 团队可在已有普通会话中挂载使用
- [ ] 团队历史恢复后显示正确团队名称
- [ ] 团队执行链路和 SSE 仍正常工作

---

### TASK-multi-agent-orchestration-验证同步-007 [验证] 运行接口/UI 验证并同步 spec 状态

**关联需求**: REQ-multi-agent-orchestration-消息路由与历史恢复
**描述**: 完成必要代码检查、接口验证、UI 验证和 TASK/CHK 状态回写。
**技术要点**: 至少包含后端启动验证、前端交互验证、同会话切换上下文验证
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `specs/task/multi-agent-orchestration/TASK-multi-agent-orchestration.md`
- `specs/checklist/multi-agent-orchestration/CHK-multi-agent-orchestration.md`

**验收标准**:
- [ ] 已执行与本次变更匹配的验证命令或 UI 操作
- [ ] 验证证据可支撑进入 done 阶段
- [ ] TASK 与 CHK 状态已同步

---

### TASK-multi-agent-orchestration-图表卡片-008 [前端] 重构图表结果卡片与详情面板层级

**关联需求**: REQ-multi-agent-orchestration-图表分析体验
**描述**: 将聊天中的图表结果从默认渲染容器改为卡片化分析组件，拆分图表区、底部信息条、详情面板，并规范标题、快捷操作和表格/图表切换布局。
**技术要点**: 优先复用现有消息卡片与图表容器；不改变消息数据结构；先收敛展示层级与壳层样式
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/components/*Chart*.jsx`（如存在）
- `frontend/src/App.jsx`

**验收标准**:
- [ ] 图表卡片存在独立图表区与底部信息条
- [ ] 标题和快捷操作不再压在绘图区
- [ ] 详情态支持表格/图表切换与配置分组展示

---

### TASK-multi-agent-orchestration-图表视觉-009 [前端] 统一图表主题色板与弱化辅助元素

**关联需求**: REQ-multi-agent-orchestration-图表分析体验
**描述**: 建立统一主题色板与图表视觉规则，统一主数据图形、图例、坐标轴、网格线、数据点和选中态的视觉权重。
**技术要点**: 固定预设主题；弱化轴线与网格；规范线宽、点大小、图例标记；禁止随机配色
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/components/*Chart*.jsx`（如存在）
- `frontend/src/styles/*` 或图表主题相关文件

**验收标准**:
- [ ] 主题色来源于固定色板
- [ ] 图例、坐标轴、网格线明显弱于主数据图形
- [ ] 选中态明确且只使用单一主强调样式

---

### TASK-multi-agent-orchestration-图表验证-010 [验证] 校验图表卡片态、详情态与视觉一致性

**关联需求**: REQ-multi-agent-orchestration-图表分析体验
**描述**: 对 BI / Excel / Team 场景下的图表结果执行界面验证，确认卡片层级、配置面板与主题一致性达到设计要求。
**技术要点**: 必须覆盖卡片态、详情态、表格/图表切换、主题色切换、长标题截断等关键场景
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `specs/task/multi-agent-orchestration/TASK-multi-agent-orchestration.md`
- `specs/checklist/multi-agent-orchestration/CHK-multi-agent-orchestration.md`

**验收标准**:
- [ ] 已验证图表卡片层级与壳层样式
- [ ] 已验证详情态配置分组和视图切换
- [ ] 已验证主题色、图例、坐标轴与选中态一致性

---

**文档结束**