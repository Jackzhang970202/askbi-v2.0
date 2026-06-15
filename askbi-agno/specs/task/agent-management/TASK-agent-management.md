# 任务清单

**版本**: v1.0
**模块**: 智能体管理 (agent-management)
**关联需求**: REQ-agent-management

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-agent-management-数据层-001 | [后端] 新建 askbi_agents 表与 CRUD 方法 | REQ-agent-management-智能体管理 | P0 | 未开始 |
| TASK-agent-management-管理器-002 | [后端] 实现 AgentManager 类 | REQ-agent-management-智能体管理 | P0 | 未开始 |
| TASK-agent-management-API-003 | [后端] 实现 Agent API 路由 | REQ-agent-management-智能体管理 | P0 | 未开始 |
| TASK-agent-management-集成-004 | [后端] Workflow 集成智能体配置加载 | REQ-agent-management-模型配置 | P0 | 未开始 |
| TASK-agent-management-前端-005 | [前端] 实现 AgentManager 页面 | REQ-agent-management-智能体管理 | P0 | 未开始 |

---

## 任务详情

### TASK-agent-management-数据层-001 新建 askbi_agents 表与 CRUD 方法

**关联需求**: REQ-agent-management-智能体管理
**描述**: 在 `config/config_db.py` 新增 `TABLE_AGENTS` 常量，在 `utils/db_utils.py` 的 `create_tables()` 新增 DDL，新增 CRUD 方法和 `seed_builtin_agents()` 种子方法。
**技术要点**: CREATE TABLE IF NOT EXISTS，JSONB 字段默认值（model_config 默认 `'{}'`，bound_skills 默认 `'[]'`），幂等种子检查（按 name 字段去重）
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `config/config_db.py`
- `utils/db_utils.py`

**验收标准**:
- [ ] 启动后端时自动创建 askbi_agents 表
- [ ] CRUD 方法可正常执行
- [ ] 内置智能体种子幂等（重复启动不重复插入，6 条固定）

---

### TASK-agent-management-管理器-002 实现 AgentManager 类

**关联需求**: REQ-agent-management-智能体管理
**描述**: 新建 `backend/agents_config/` 模块，实现 AgentManager 类封装智能体的 CRUD、模型配置合并、技能绑定、对话测试等业务逻辑。
**技术要点**: model_config 合并策略为字段级覆盖（空值回退 config.json），api_key 脱敏返回后 4 位，测试方法构建临时 Agent 实例
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/agents_config/__init__.py`
- `backend/agents_config/agent_manager.py`

**验收标准**:
- [ ] AgentManager 的 list/get/create/update/delete 方法正常工作
- [ ] get_merged_model_config 正确合并智能体配置与全局默认值
- [ ] bind_skills 校验技能 ID 有效性后更新
- [ ] test_agent 使用临时 Agent 返回回复
- [ ] 内置智能体删除返回错误

---

### TASK-agent-management-API-003 实现 Agent API 路由

**关联需求**: REQ-agent-management-智能体管理
**描述**: 新建 `backend/agents_config/agent_api.py` FastAPI 路由，挂载到 `backend_api_agno.py`。实现 6 个端点。
**技术要点**: FastAPI Router，Bearer token 认证，角色权限校验（admin/manager），api_key 脱敏响应
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/agents_config/agent_api.py`
- `backend_api_agno.py`

**验收标准**:
- [ ] 所有 6 个端点可正常调用
- [ ] 内置智能体删除返回 403
- [ ] 非 admin/manager 创建/修改返回 403
- [ ] api_key 在 GET 响应中脱敏（仅显示后 4 位）
- [ ] temperature 超出 0-2 范围返回 400

---

### TASK-agent-management-集成-004 Workflow 集成智能体配置加载

**关联需求**: REQ-agent-management-模型配置
**描述**: 在 `bi_workflow.py` 和 `askexcel_workflow.py` 中修改 Agent 构建逻辑，从 DB 加载智能体的 base_instructions 和 model_config，替代硬编码值。DB 无记录时回退到原有硬编码默认值。
**技术要点**: 不改变现有工作流结构，仅替换 Agent 实例化时的 instructions 和 model 参数来源
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/workflows/askexcel_workflow.py`

**验收标准**:
- [ ] BI 问数使用 DB 中 bi_sql_agent 的 base_instructions
- [ ] BI 报告生成使用 DB 中 bi_report_agent 的 base_instructions
- [ ] BI 图表生成使用 DB 中 bi_chart_agent 的 base_instructions
- [ ] Excel 分析使用 DB 中对应 agent 的 base_instructions
- [ ] model_config 覆盖正确应用（model、temperature、api_key、base_url）
- [ ] DB 无记录时行为与升级前一致

---

### TASK-agent-management-前端-005 实现 AgentManager 页面

**关联需求**: REQ-agent-management-智能体管理
**描述**: 新建 `AgentManager.jsx` 组件，实现智能体卡片网格、编辑面板（base_instructions 编辑器、model_config 表单、技能绑定多选）、对话测试面板。在 Sidebar 新增导航入口，在 App.jsx 新增路由和 tab 分发。
**技术要点**: 卡片网格响应式布局，textarea 编辑器（monospace），温度滑块控件，api_key 脱敏展示，对话测试简单聊天 UI
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/AgentManager.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`

**验收标准**:
- [ ] 智能体卡片网格正确展示，显示名称/描述/状态/技能数量
- [ ] 编辑面板可正常创建/编辑智能体
- [ ] base_instructions textarea 编辑器正常工作
- [ ] model_config 表单（模型名称、温度滑块、api_key、base_url）正常
- [ ] 技能绑定多选列表可正常选择/取消选择
- [ ] 对话测试面板可发送消息并展示回复
- [ ] 内置智能体不显示删除按钮
- [ ] 侧边栏导航可正确跳转
