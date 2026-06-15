# 检查清单

**版本**: v1.0
**模块**: 技能系统 (skill-system)
**关联需求**: REQ-skill-system

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-skill-system-CRUD-001 | 技能 CRUD 操作完整性 | REQ-skill-system-技能管理 | 阻塞 | 未开始 |
| CHK-skill-system-内置保护-002 | 内置技能不可删除 | REQ-skill-system-技能管理 | 阻塞 | 未开始 |
| CHK-skill-system-注入-003 | 技能注入到 system prompt | REQ-skill-system-技能注入 | 阻塞 | 未开始 |
| CHK-skill-system-过滤-004 | 绑定与作用域过滤正确性 | REQ-skill-system-技能注入 | 重要 | 未开始 |
| CHK-skill-system-缓存-005 | 技能缓存 TTL 生效 | REQ-skill-system-技能注入 | 重要 | 未开始 |
| CHK-skill-system-种子-006 | 内置技能种子幂等性 | REQ-skill-system-技能管理 | 阻塞 | 未开始 |
| CHK-skill-system-前端-007 | 技能管理页面完整功能 | REQ-skill-system-技能管理 | 阻塞 | 未开始 |

---

## 检查项详情

### CHK-skill-system-CRUD-001 技能 CRUD 操作完整性

**关联需求**: REQ-skill-system-技能管理
**目的**: 验证技能增删改查全流程
**方法**: API 端到端测试
**等级**: 阻塞

**检查步骤**:
1. 调用 `POST /skills` 创建新技能，确认返回成功
2. 调用 `GET /skills` 确认新技能出现在列表中
3. 调用 `PUT /skills/{id}` 修改 instructions，确认更新成功
4. 调用 `DELETE /skills/{id}` 删除非内置技能，确认删除成功

**预期结果**:
- 所有 CRUD 操作返回 `success: true`
- 数据库记录与 API 响应一致

---

### CHK-skill-system-内置保护-002 内置技能不可删除

**关联需求**: REQ-skill-system-技能管理
**目的**: 验证内置技能的保护机制
**方法**: 尝试删除内置技能
**等级**: 阻塞

**检查步骤**:
1. 获取一个 `is_builtin=TRUE` 的技能 ID
2. 调用 `DELETE /skills/{id}` 尝试删除
3. 调用 `PATCH /skills/{id}/toggle` 尝试禁用

**预期结果**:
- 删除操作返回错误"内置技能不可删除"
- 禁用操作正常执行（允许禁用内置技能）

---

### CHK-skill-system-注入-003 技能注入到 system prompt

**关联需求**: REQ-skill-system-技能注入
**目的**: 验证技能内容被正确注入到 LLM 调用的 system prompt
**方法**: 端到端问答 + 日志检查
**等级**: 阻塞

**检查步骤**:
1. 创建一个具有明确标记文本的技能（如 `## SKILL_MARKER_TEST`）
2. 发送 BI 问数问题
3. 检查后端日志中 LLM 请求的 system prompt 是否包含标记文本

**预期结果**:
- system prompt 中包含技能的 instructions 内容
- 无技能时 system prompt 与升级前一致

---

### CHK-skill-system-过滤-004 绑定与作用域过滤正确性

**关联需求**: REQ-skill-system-技能注入
**目的**: 验证技能的绑定智能体和数据源作用域过滤逻辑
**方法**: 组合测试
**等级**: 重要

**检查步骤**:
1. 创建绑定到 `bi_sql_agent` 的技能，发送 BI 问题，确认注入
2. 创建绑定到 `bi_report_agent` 的技能，发送 BI 问题，确认不注入到 SQL 步骤
3. 创建 scope_type=specific 的技能，使用不同数据源验证

**预期结果**:
- 技能只注入到匹配的智能体
- 技能只在匹配的数据源下注入

---

### CHK-skill-system-缓存-005 技能缓存 TTL 生效

**关联需求**: REQ-skill-system-技能注入
**目的**: 验证技能查询缓存减少 DB 访问
**方法**: 连续多次问答，观察 DB 查询日志
**等级**: 重要

**检查步骤**:
1. 发送第一次问数请求，确认 DB 查询执行
2. 立即发送第二次问数请求，确认命中缓存（无新 DB 查询）
3. 等待 60 秒后再次发送请求，确认缓存刷新

**预期结果**:
- 60 秒内的重复请求不触发新的 DB 查询
- 60 秒后缓存自动刷新

---

### CHK-skill-system-种子-006 内置技能种子幂等性

**关联需求**: REQ-skill-system-技能管理
**目的**: 验证重复启动不会重复插入种子数据
**方法**: 多次启动后端服务
**等级**: 阻塞

**检查步骤**:
1. 启动后端服务
2. 查询 `SELECT count(*) FROM askbi_skills WHERE is_builtin=TRUE`
3. 重启后端服务
4. 再次查询确认数量不变

**预期结果**:
- 内置技能数量固定（3 条）
- 重复启动不增加记录

---

### CHK-skill-system-前端-007 技能管理页面完整功能

**关联需求**: REQ-skill-system-技能管理
**目的**: 验证前端技能管理页面的完整功能
**方法**: 手动 UI 测试
**等级**: 阻塞

**检查步骤**:
1. 导航到技能管理页面，确认列表加载
2. 点击新建技能，填写表单，保存
3. 编辑已有技能，修改 instructions，保存
4. 切换技能状态开关
5. 尝试删除内置技能（按钮应禁用）
6. 使用分类筛选

**预期结果**:
- 所有操作正常
- UI 反馈及时准确
