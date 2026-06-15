# 检查清单

**版本**: v1.0
**模块**: 全局配置 (global-configs)
**关联需求**: REQ-global-configs

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-global-configs-CRUD-001 | 配置 CRUD 功能 | REQ-global-configs-配置CRUD | 阻塞 | 已完成 |
| CHK-global-configs-权限-002 | 用户权限过滤 | REQ-global-configs-配置CRUD | 阻塞 | 已完成 |
| CHK-global-configs-报表规则-003 | 报表规则加载 | REQ-global-configs-报表规则 | 阻塞 | 已完成 |
| CHK-global-configs-切换-004 | 启用/禁用切换 | REQ-global-configs-配置CRUD | 重要 | 已完成 |

---

## 检查项详情

### CHK-global-configs-CRUD-001 配置 CRUD 功能

**关联需求**: REQ-global-configs-配置CRUD
**目的**: 验证全局配置的增删改查
**方法**: CRUD 测试
**等级**: 阻塞

**检查步骤**:
1. 创建配置 (category, name, content)
2. 查看列表，验证包含新配置
3. 更新配置 (传入 id)，验证内容更新
4. 切换启用状态，验证 is_enabled 变化
5. 删除配置，验证列表中不再出现

**预期结果**:
- CRUD 操作正常
- upsert 逻辑正确 (创建/更新)

### CHK-global-configs-权限-002 用户权限过滤

**关联需求**: REQ-global-configs-配置CRUD
**目的**: 验证配置可见性控制
**方法**: 多角色测试
**等级**: 阻塞

**检查步骤**:
1. admin 创建配置
2. 普通用户查看列表，验证是否可见 (全局配置可见，用户级配置不可见)
3. admin 查看所有配置

**预期结果**:
- 权限过滤正确

### CHK-global-configs-报表规则-003 报表规则加载

**关联需求**: REQ-global-configs-报表规则
**目的**: 验证报表生成正确加载规则配置
**方法**: 端到端测试
**等级**: 阻塞

**检查步骤**:
1. 配置报表规则 (category=report_rule)
2. 启用规则
3. 生成报表，验证规则被正确加载
4. 禁用规则，验证报表生成返回错误

**预期结果**:
- 报表规则正确加载与匹配

---

## 交付检查

| 编号 | 检查项 | 等级 | 状态 |
|------|--------|------|------|
| CHK-DELIVER-001 | 代码已提交 | 阻塞 | 未开始 |
| CHK-DELIVER-002 | 代码审查通过 | 阻塞 | 未开始 |

---

**文档结束**
