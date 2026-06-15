# 检查清单

**版本**: v1.1
**模块**: 记忆管理 (memory-management)
**关联需求**: REQ-memory-management

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | automation | 状态 |
|------|--------|----------|------|------------|------|
| CHK-memory-management-表结构-001 | 记忆表结构完整性 | REQ-memory-management-用户画像记忆 / 会话记忆 | 阻塞 | static | 待执行 |
| CHK-memory-management-用户画像-002 | 用户画像记忆抽取与注入 | REQ-memory-management-用户画像记忆 | 阻塞 | manual | 待执行 |
| CHK-memory-management-会话记忆-003 | 会话记忆抽取与隔离 | REQ-memory-management-会话记忆 | 阻塞 | manual | 待执行 |
| CHK-memory-management-权限-004 | 记忆访问权限隔离 | REQ-memory-management-管理与可视化 | 阻塞 | static | 待执行 |
| CHK-memory-management-mem0-005 | mem0 主链路接入与 SQLite→PostgreSQL 持久化替换 | REQ-memory-management-mem0集成 | 阻塞 | manual | 待执行 |
| CHK-memory-management-管理页-006 | 记忆管理页面功能 | REQ-memory-management-管理与可视化 | 重要 | manual | 待执行 |
| CHK-memory-management-手动修改-009 | 用户画像与会话摘要记忆可手动修改 | REQ-memory-management-管理与可视化 | 重要 | manual | 待执行 |
| CHK-memory-management-删除联动-007 | 会话删除联动清理记忆 | REQ-memory-management-会话记忆 | 阻塞 | static | 待执行 |
| CHK-memory-management-全量存库-008 | 问答内容和选项全量存库 | REQ-memory-management-用户画像记忆 / 会话记忆 | 阻塞 | static | 待执行 |

---

## 检查项详情

### CHK-memory-management-表结构-001 记忆表结构完整性

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**目的**: 验证 PostgreSQL 记忆表、字段、约束和事件表齐全。  
**方法**: 静态检查 + 数据库检查  
**等级**: 阻塞 | **automation**: static

**检查步骤**:
1. 检查 `config/config_db.py` 是否定义三张表常量。
2. 检查 `utils/db_utils.py#create_tables()` 是否创建三张表。
3. 检查用户画像表是否包含 `user_id/memory_kind/profile_text/dedupe_key/status`。
4. 检查会话记忆表是否包含 `chat_id/memory_kind/profile_text/dedupe_key/status`。
5. 检查事件表是否记录 `memory_scope/event_type/event_payload`。

**预期结果**:
- 三张表可自动创建
- 字段满足 DES 定义
- dedupe 唯一约束存在或由 upsert 逻辑保证

---

### CHK-memory-management-用户画像-002 用户画像记忆抽取与注入

**关联需求**: REQ-memory-management-用户画像记忆  
**目的**: 验证长期用户画像可自动总结并注入后续对话。  
**方法**: 手动端到端测试  
**等级**: 阻塞 | **automation**: manual

**检查步骤**:
1. 用户 A 发送包含长期偏好的问题，例如“以后回答尽量用表格”。
2. 等待记忆抽取完成。
3. 查询 `askbi_user_profile_memory` 是否出现 preference 类型记录。
4. 用户 A 新建会话提问，观察模型上下文或结果是否体现该偏好。

**预期结果**:
- 用户画像被写入 PG
- 后续新会话可注入该画像
- 记忆抽取失败不影响原始问答

---

### CHK-memory-management-会话记忆-003 会话记忆抽取与隔离

**关联需求**: REQ-memory-management-会话记忆  
**目的**: 验证会话级记忆只在当前会话生效。  
**方法**: 手动端到端测试  
**等级**: 阻塞 | **automation**: manual

**检查步骤**:
1. 在会话 A 中确认一个统计口径。
2. 查询 `askbi_session_profile_memory` 是否写入 decision/state。
3. 在会话 A 后续问题中验证该口径可被使用。
4. 切换到会话 B，验证不会注入会话 A 的记忆。

**预期结果**:
- 会话 A 有对应记忆
- 会话 A 后续问题可使用
- 会话 B 不共享该会话记忆

---

### CHK-memory-management-权限-004 记忆访问权限隔离

**关联需求**: REQ-memory-management-管理与可视化  
**目的**: 验证普通用户不能读取、归档、删除其他用户的记忆。  
**方法**: API 权限测试  
**等级**: 阻塞 | **automation**: static

**检查步骤**:
1. 使用用户 A 创建记忆。
2. 使用用户 B 调用用户 A 的记忆详情/删除接口。
3. 使用 admin 调用按用户筛选接口。

**预期结果**:
- 用户 B 请求返回 403 或空结果
- admin/manager 可按权限筛选
- 所有管理操作写审计事件

---

### CHK-memory-management-mem0-005 mem0 同步降级

**关联需求**: REQ-memory-management-mem0集成  
**目的**: 验证 mem0 是记忆读写主链路，且系统不会静默降级为 PostgreSQL-only。  
**方法**: 配置切换测试  
**等级**: 重要 | **automation**: manual

**检查步骤**:
1. 创建一条新记忆，确认实际调用 mem0 并返回 `mem0_id`。
2. 查询 PG 映射表，确认记录了 `mem0_id` 与审计信息。
3. 触发一次记忆检索，确认主链路来自 mem0。
4. 模拟 mem0 不可用，再执行记忆写入/检索。

**预期结果**:
- mem0 可用时新增、检索、更新都实际经过 mem0
- PG 仅保存映射与审计信息
- mem0 不可用时接口显式报错，不发生 PostgreSQL-only 降级

---

### CHK-memory-management-管理页-006 记忆管理页面功能

**关联需求**: REQ-memory-management-管理与可视化  
**目的**: 验证前端页面可管理用户画像和会话记忆。  
**方法**: 手动 UI 测试  
**等级**: 重要 | **automation**: manual

**检查步骤**:
1. 打开记忆管理页。
2. 查询用户画像列表。
3. 切换会话记忆 Tab 并筛选 chat_id。
4. 打开详情抽屉查看完整 profile_json/profile_text。
5. 归档或删除一条记忆。

**预期结果**:
- 列表、筛选、详情、归档、删除均正常
- 操作后 UI 状态即时刷新

---

### CHK-memory-management-删除联动-007 会话删除联动清理记忆

**关联需求**: REQ-memory-management-会话记忆  
**目的**: 验证删除会话不会留下活跃会话记忆。  
**方法**: API/代码检查  
**等级**: 阻塞 | **automation**: static

**检查步骤**:
1. 创建会话并生成会话记忆。
2. 删除该会话。
3. 查询 `askbi_session_profile_memory` 中该 chat_id 的 active 记录。
4. 查询 `askbi_memory_events` 是否存在清理事件。

**预期结果**:
- 删除后无 active 会话记忆
- 清理事件被记录

---

### CHK-memory-management-全量存库-008 问答内容和选项全量存库

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**目的**: 验证记忆抽取前，当前轮对话内容、结构化结果和用户选项已完整入库。  
**方法**: 静态检查 + 问答后 DB 检查  
**等级**: 阻塞 | **automation**: static

**检查步骤**:
1. 发送 BI 问数，包含技能选择、分析开关、数据源。
2. 查询 `askbi_messages.structured_data` 是否包含回复、SQL/图表/结果和 request_options。
3. 查询 `askbi_request_record` 是否包含问题、检索信息、执行结果。
4. 对 Excel 问数重复以上检查。

**预期结果**:
- user/assistant 消息均已入库
- assistant structured_data 包含后续记忆抽取所需上下文
- 保存失败时接口不应假成功

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2026-06-15 | 初始版本：生成记忆管理检查清单 | zhangqiyuan |

---

**文档结束**
