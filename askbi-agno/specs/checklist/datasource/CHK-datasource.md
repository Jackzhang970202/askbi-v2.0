# 检查清单

**版本**: v1.0
**模块**: 数据源管理 (datasource)
**关联需求**: REQ-datasource

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-datasource-PG-001 | PostgreSQL 连接与操作 | REQ-datasource-数据源CRUD | 阻塞 | 已完成 |
| CHK-datasource-MySQL-002 | MySQL 连接与操作 | REQ-datasource-数据源CRUD | 阻塞 | 已完成 |
| CHK-datasource-CRUD-003 | 数据源 CRUD 功能 | REQ-datasource-数据源CRUD | 阻塞 | 已完成 |
| CHK-datasource-连接测试-004 | 连接测试功能 | REQ-datasource-连接测试 | 阻塞 | 已完成 |
| CHK-datasource-元数据-005 | 元数据生成与存储 | REQ-datasource-元数据生成 | 阻塞 | 已完成 |
| CHK-datasource-隔离-006 | 用户数据隔离 | REQ-datasource-数据源CRUD | 阻塞 | 已完成 |
| CHK-datasource-跨Schema-007 | 跨 Schema 支持 | REQ-datasource-跨Schema支持 | 重要 | 已完成 |
| CHK-datasource-前端-008 | 前端配置界面 | REQ-datasource-数据源CRUD | 阻塞 | 已完成 |

---

## 检查项详情

### CHK-datasource-CRUD-003 数据源 CRUD 功能

**关联需求**: REQ-datasource-数据源CRUD
**目的**: 验证数据源增删改查功能
**方法**: CRUD 端到端测试
**等级**: 阻塞

**检查步骤**:
1. 创建 PostgreSQL 数据源，验证连接测试与配置保存
2. 创建 MySQL 数据源，验证连接测试
3. 创建 Excel 数据源，验证文件上传与保存
4. 查看列表，验证用户过滤
5. 查看详情，验证配置完整
6. 删除数据源，验证连接关闭、配置删除、文件清理

**预期结果**:
- 所有 CRUD 操作正常
- 删除后数据完全清理

### CHK-datasource-元数据-005 元数据生成与存储

**关联需求**: REQ-datasource-元数据生成
**目的**: 验证元数据生成正确性
**方法**: 生成后验证
**等级**: 阻塞

**检查步骤**:
1. PG 数据源生成元数据，验证存入 askbi_chat_knowledge
2. Excel 数据源生成元数据，验证存入 refer/ 目录
3. 验证元数据包含表名、列信息、注释、样例数据
4. 通过 /refer/schema 查看元数据

**预期结果**:
- 元数据完整
- 存储位置正确
- 可查看

### CHK-datasource-隔离-006 用户数据隔离

**关联需求**: REQ-datasource-数据源CRUD
**目的**: 验证数据源用户隔离
**方法**: 多用户测试
**等级**: 阻塞

**检查步骤**:
1. 用户 A 创建数据源
2. 用户 B 登录，列表中看不到用户 A 的数据源
3. admin 登录，可以看到所有数据源

**预期结果**:
- 普通用户仅见自己的数据源
- admin/manager 可见全部

---

## 交付检查

| 编号 | 检查项 | 等级 | 状态 |
|------|--------|------|------|
| CHK-DELIVER-001 | 代码已提交 | 阻塞 | 未开始 |
| CHK-DELIVER-002 | 代码审查通过 | 阻塞 | 未开始 |

---

**文档结束**
