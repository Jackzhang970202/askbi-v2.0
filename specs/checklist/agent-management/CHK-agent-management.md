# 检查清单

**版本**: v1.0
**模块**: 智能体管理 (agent-management)
**关联需求**: REQ-agent-management

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-agent-management-CRUD-001 | 智能体 CRUD 操作完整性 | REQ-agent-management-智能体管理 | 阻塞 | 未开始 |
| CHK-agent-management-内置保护-002 | 内置智能体不可删除 | REQ-agent-management-智能体管理 | 阻塞 | 未开始 |
| CHK-agent-management-模型配置-003 | 模型配置覆盖与回退 | REQ-agent-management-模型配置 | 阻塞 | 未开始 |
| CHK-agent-management-对话测试-004 | 对话测试功能 | REQ-agent-management-对话测试 | 重要 | 未开始 |
| CHK-agent-management-技能绑定-005 | 技能绑定与解绑 | REQ-agent-management-技能绑定 | 阻塞 | 未开始 |
| CHK-agent-management-种子-006 | 内置智能体种子幂等性 | REQ-agent-management-智能体管理 | 阻塞 | 未开始 |
| CHK-agent-management-前端-007 | 智能体管理页面完整功能 | REQ-agent-management-智能体管理 | 阻塞 | 未开始 |

---

## 检查项详情

### CHK-agent-management-CRUD-001 智能体 CRUD 操作完整性

**关联需求**: REQ-agent-management-智能体管理
**目的**: 验证智能体增删改查全流程
**方法**: API 端到端测试
**等级**: 阻塞

**检查步骤**:
1. 调用 `GET /agents` 确认返回 6 个内置智能体
2. 调用 `POST /agents` 创建自定义智能体，确认返回成功
3. 调用 `GET /agents` 确认新智能体出现在列表中（共 7 个）
4. 调用 `PUT /agents/{id}` 修改 base_instructions，确认更新成功
5. 调用 `DELETE /agents/{id}` 删除自定义智能体，确认删除成功

**预期结果**:
- 所有 CRUD 操作返回 `success: true`
- 数据库记录与 API 响应一致
- 内置智能体数量固定为 6

---

### CHK-agent-management-内置保护-002 内置智能体不可删除

**关联需求**: REQ-agent-management-智能体管理
**目的**: 验证内置智能体的删除保护机制
**方法**: 尝试删除内置智能体
**等级**: 阻塞

**检查步骤**:
1. 获取一个 `is_builtin=TRUE` 的智能体 ID
2. 调用 `DELETE /agents/{id}` 尝试删除
3. 调用 `PUT /agents/{id}` 修改 base_instructions（应允许）

**预期结果**:
- 删除操作返回错误"内置智能体不可删除"（HTTP 403）
- 编辑操作正常执行（允许编辑内置智能体配置）

---

### CHK-agent-management-模型配置-003 模型配置覆盖与回退

**关联需求**: REQ-agent-management-模型配置
**目的**: 验证智能体模型配置的覆盖和回退逻辑
**方法**: 设置与不设置 model_config 分别测试
**等级**: 阻塞

**检查步骤**:
1. 获取一个 model_config 为空的内置智能体
2. 发送问数请求，确认使用 config.json 默认模型配置
3. 调用 `PUT /agents/{id}` 设置 model_config（指定 model 和 temperature）
4. 再次发送问数请求，确认使用智能体自定义配置
5. 将 model_config 中 model 字段清空，确认回退到 config.json 默认模型

**预期结果**:
- 空 model_config 使用 config.json 全局默认值
- 设置 model_config 后使用智能体自定义值
- 字段级覆盖：设置 model 不影响 temperature 的回退

---

### CHK-agent-management-对话测试-004 对话测试功能

**关联需求**: REQ-agent-management-对话测试
**目的**: 验证对话测试面板使用智能体当前配置进行对话
**方法**: API 调用测试
**等级**: 重要

**检查步骤**:
1. 选择一个已启用的智能体
2. 调用 `POST /agents/{id}/test` 发送测试消息
3. 修改智能体的 base_instructions
4. 再次调用测试接口，确认回复基于新的 instructions
5. 对已禁用的智能体调用测试接口

**预期结果**:
- 测试回复内容与智能体配置一致
- 修改 instructions 后测试使用最新配置
- 禁用智能体测试返回错误提示
- 测试对话不写入 askbi_messages 表

---

### CHK-agent-management-技能绑定-005 技能绑定与解绑

**关联需求**: REQ-agent-management-技能绑定
**目的**: 验证技能绑定和解绑操作的正确性
**方法**: API 调用 + 工作流验证
**等级**: 阻塞

**检查步骤**:
1. 调用 `POST /agents/{id}/bind-skills` 绑定技能 [1, 2]
2. 调用 `GET /agents/{id}` 确认 bound_skills 为 [1, 2]
3. 调用 `POST /agents/{id}/bind-skills` 绑定技能 [1, 3, 999]（999 不存在）
4. 确认 bound_skills 为 [1, 3]（不存在的 ID 被过滤）
5. 调用 `POST /agents/{id}/bind-skills` 绑定空数组 []
6. 确认 bound_skills 为 []

**预期结果**:
- 绑定操作为全量替换
- 不存在的技能 ID 被忽略不报错
- 空数组表示解绑所有技能
- 绑定的技能在智能体执行时被正确注入

---

### CHK-agent-management-种子-006 内置智能体种子幂等性

**关联需求**: REQ-agent-management-智能体管理
**目的**: 验证重复启动不会重复插入种子数据
**方法**: 多次启动后端服务
**等级**: 阻塞

**检查步骤**:
1. 启动后端服务
2. 查询 `SELECT count(*) FROM askbi_agents WHERE is_builtin=TRUE`
3. 重启后端服务
4. 再次查询确认数量不变

**预期结果**:
- 内置智能体数量固定（6 条）
- 重复启动不增加记录

---

### CHK-agent-management-前端-007 智能体管理页面完整功能

**关联需求**: REQ-agent-management-智能体管理
**目的**: 验证前端智能体管理页面的完整功能
**方法**: 手动 UI 测试
**等级**: 阻塞

**检查步骤**:
1. 导航到智能体管理页面，确认卡片网格加载（6 张卡片）
2. 确认每张卡片显示名称、描述、状态、技能数量
3. 点击"新建智能体"，填写表单，保存
4. 点击某卡片"编辑"，修改 base_instructions，保存
5. 编辑面板中修改 model_config（温度滑块、模型名称等）
6. 点击"绑定技能"，选择技能，确认绑定
7. 点击"测试"，发送消息，查看回复
8. 尝试删除内置智能体（按钮应不显示）
9. 删除自定义智能体，确认弹窗后删除成功

**预期结果**:
- 所有操作正常
- UI 反馈及时准确
- 内置智能体无删除入口
- 对话测试面板正常收发消息
