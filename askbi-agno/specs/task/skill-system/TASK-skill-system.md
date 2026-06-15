# 任务清单

**版本**: v1.0
**模块**: 技能系统 (skill-system)
**关联需求**: REQ-skill-system

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-skill-system-数据层-001 | [后端] 新建 askbi_skills 表与 CRUD 方法 | REQ-skill-system-技能管理 | P0 | 未开始 |
| TASK-skill-system-管理器-002 | [后端] 实现 SkillManager + SkillRegistry | REQ-skill-system-技能注入 | P0 | 未开始 |
| TASK-skill-system-API-003 | [后端] 实现 Skill API 路由 | REQ-skill-system-技能管理 | P0 | 未开始 |
| TASK-skill-system-注入-004 | [后端] Workflow 集成技能注入 | REQ-skill-system-技能注入 | P0 | 未开始 |
| TASK-skill-system-前端-005 | [前端] 实现 SkillManager 页面 | REQ-skill-system-技能管理 | P0 | 未开始 |
| TASK-skill-system-AI-006 | [后端] 实现 AI 辅助创建接口 | REQ-skill-system-AI辅助创建 | P1 | 未开始 |
| TASK-skill-system-测试-007 | [前后端] 实现技能测试面板 | REQ-skill-system-技能测试 | P1 | 未开始 |

---

## 任务详情

### TASK-skill-system-数据层-001 新建 askbi_skills 表与 CRUD 方法

**关联需求**: REQ-skill-system-技能管理
**描述**: 在 `config/config_db.py` 新增 `TABLE_SKILLS` 常量，在 `utils/db_utils.py` 的 `create_tables()` 新增 DDL，新增 CRUD 方法和 `seed_builtin_skills()` 种子方法。
**技术要点**: CREATE TABLE IF NOT EXISTS，JSONB 字段默认值，幂等种子检查
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `config/config_db.py`
- `utils/db_utils.py`

**验收标准**:
- [ ] 启动后端时自动创建 askbi_skills 表
- [ ] CRUD 方法可正常执行
- [ ] 内置技能种子幂等（重复启动不重复插入）

---

### TASK-skill-system-管理器-002 实现 SkillManager + SkillRegistry

**关联需求**: REQ-skill-system-技能注入
**描述**: 新建 `backend/skills/` 模块，实现 SkillManager（CRUD 封装）和 SkillRegistry（运行时加载 + 60s TTL 缓存 + prompt 拼接）。
**技术要点**: 缓存使用 dict + timestamp TTL，prompt 拼接格式为 `\n\n## 附加规则\n{instructions}`
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/skills/__init__.py`
- `backend/skills/skill_manager.py`
- `backend/skills/skill_registry.py`

**验收标准**:
- [ ] SkillManager 的 list/get/create/update/delete/toggle 方法正常工作
- [ ] SkillRegistry 按 agent_name + datasource 正确过滤技能
- [ ] 缓存 TTL 生效（60s 内不重复查 DB）

---

### TASK-skill-system-API-003 实现 Skill API 路由

**关联需求**: REQ-skill-system-技能管理
**描述**: 新建 `backend/skills/skill_api.py` FastAPI 路由，挂载到 `backend_api_agno.py`。实现 7 个端点。
**技术要点**: FastAPI Router，Bearer token 认证，角色权限校验
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/skills/skill_api.py`
- `backend_api_agno.py`

**验收标准**:
- [ ] 所有 7 个端点可正常调用
- [ ] 内置技能删除返回 403
- [ ] 非 admin/manager 创建返回 403

---

### TASK-skill-system-注入-004 Workflow 集成技能注入

**关联需求**: REQ-skill-system-技能注入
**描述**: 在 `bi_workflow.py` 和 `askexcel_workflow.py` 中新增 `_build_system_prompt()` 方法，每个 `_llm()` 调用点传入 agent_name，加载并注入匹配的技能 instructions。
**技术要点**: 不改变现有 `_llm()` 签名，通过新方法构建 system prompt 后传入
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/workflows/askexcel_workflow.py`

**验收标准**:
- [ ] BI 问数时技能被正确注入到 SQL 生成、报告生成、图表生成的 system prompt
- [ ] Excel 问数时技能被正确注入
- [ ] 无活跃技能时系统行为与升级前一致

---

### TASK-skill-system-前端-005 实现 SkillManager 页面

**关联需求**: REQ-skill-system-技能管理
**描述**: 新建 `SkillManager.jsx` 组件，实现技能列表、编辑面板、分类筛选、状态切换、CRUD 操作。在 Sidebar 新增导航入口，在 App.jsx 新增路由和 tab 分发。
**技术要点**: 参照 GlobalConfigManager 的 CRUD 管理模式，textarea 编辑器
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/SkillManager.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`

**验收标准**:
- [ ] 技能列表正确展示，支持分类筛选
- [ ] 编辑面板可正常创建/编辑技能
- [ ] 状态开关切换即时生效
- [ ] 侧边栏导航可正确跳转

---

### TASK-skill-system-AI-006 实现 AI 辅助创建接口

**关联需求**: REQ-skill-system-AI辅助创建
**描述**: 实现 `POST /skills/ai-create` 接口，调用 LLM 根据描述生成 instructions 内容。前端编辑面板增加"AI 优化"按钮。
**技术要点**: 复用现有 OpenAI client，构建专用 prompt 模板
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/skills/skill_api.py`
- `frontend/src/components/SkillManager.jsx`

**验收标准**:
- [ ] AI 生成的 instructions 内容结构化且合理
- [ ] 前端可预览并二次编辑

---

### TASK-skill-system-测试-007 实现技能测试面板

**关联需求**: REQ-skill-system-技能测试
**描述**: 实现 `POST /skills/{id}/test` 接口和前端测试面板。用户选择 agent + 数据源 + 问题后预览注入后的完整 prompt。
**技术要点**: 后端模拟加载流程但不实际调用 LLM，前端可折叠面板
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/skills/skill_api.py`
- `frontend/src/components/SkillManager.jsx`

**验收标准**:
- [ ] 测试面板正确展示注入后的完整 prompt
- [ ] 不同 agent/datasource 组合展示不同的注入结果
