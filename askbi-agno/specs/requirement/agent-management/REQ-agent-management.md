# 智能体管理模块 - 需求文档

**版本**: v1.0
**模块**: 智能体管理 (agent-management)

---

## REQ-agent-management-智能体管理

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
系统提供可视化的智能体（Agent）管理功能，支持对现有 6 个内置智能体（bi_sql_agent、bi_report_agent、bi_chart_agent、askexcel_code_agent、askexcel_report_agent、askexcel_chart_agent）进行配置管理，替代硬编码的系统提示词。管理员可以查看、编辑智能体的基础指令（base_instructions）、模型配置、工具列表等属性，并可创建自定义智能体。内置智能体不可删除但可编辑配置。

### 前置条件
- 用户已登录且具有 admin 或 manager 角色
- 数据库已创建 `askbi_agents` 表
- 系统启动时已种子内置智能体

### 输入
- 智能体名称（name）、显示名称（display_name）、描述（description）
- 基础指令（base_instructions，系统提示词 Markdown 文本）
- 模型配置（model_config，JSON 格式：model、temperature、api_key、base_url）
- 绑定技能（bound_skills，JSON 数组，技能 ID 列表）
- 工具配置（tools，JSON 格式）
- 启用状态（is_active）

### 输出
- 智能体列表（卡片网格展示）
- 智能体详情
- 操作结果（创建/更新/删除/绑定技能）

### 处理规则
1. 创建智能体时 name 不可重复
2. 内置智能体（`is_builtin=TRUE`）不可删除，但可编辑 base_instructions、model_config 等配置
3. 仅 admin 和 manager 角色可执行创建和修改操作
4. 智能体 name 为系统标识符，创建后不可修改
5. 删除自定义智能体前需确认，解除所有技能绑定

### 验收标准
- [ ] 可查看所有智能体列表（卡片网格形式）
- [ ] 可编辑智能体的 base_instructions 并保存到数据库
- [ ] 可创建自定义智能体并保存
- [ ] 可删除非内置智能体
- [ ] 内置智能体不可删除但可编辑
- [ ] 仅 admin/manager 可执行写操作

---

## REQ-agent-management-模型配置

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
每个智能体支持独立的模型配置覆盖，包括模型名称（model）、温度参数（temperature）、API 密钥（api_key）、API 地址（base_url）。当智能体配置了模型参数时使用智能体自身配置，未配置时回退到 config.json 中的全局默认值。

### 前置条件
- 智能体已创建
- config.json 中存在全局默认模型配置

### 输入
- model_config JSON 对象：
  - model（字符串，模型名称，可选）
  - temperature（浮点数，0-2，可选）
  - api_key（字符串，API 密钥，可选）
  - base_url（字符串，API 地址，可选）

### 输出
- 更新后的智能体配置
- 工作流执行时使用合并后的模型配置

### 处理规则
1. model_config 中每个字段独立覆盖，空值表示使用 config.json 默认值
2. 合并优先级：智能体 model_config > config.json 全局配置
3. api_key 在前端展示时脱敏处理（仅显示后 4 位）
4. temperature 取值范围 0-2，超出范围返回校验错误

### 验收标准
- [ ] 可为智能体设置独立的 model 名称
- [ ] 可为智能体设置独立的 temperature
- [ ] 可为智能体设置独立的 api_key 和 base_url
- [ ] 未设置时使用 config.json 默认值
- [ ] api_key 在前端脱敏展示
- [ ] temperature 超出范围时返回错误提示

---

## REQ-agent-management-对话测试

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P1

### 需求描述
用户可在智能体管理界面打开对话测试面板，使用智能体当前的完整配置（base_instructions + model_config + bound_skills）发送一条消息，查看智能体的回复，验证配置效果。

### 前置条件
- 智能体已创建且 `is_active=TRUE`
- 智能体的模型配置有效（或 config.json 默认值有效）

### 输入
- 智能体 ID
- 用户消息文本

### 输出
- 智能体的回复文本

### 处理规则
1. 使用智能体当前的 base_instructions 作为 system prompt
2. 应用智能体的 model_config 覆盖（合并 config.json 默认值）
3. 加载智能体绑定的技能 instructions 注入到 system prompt
4. 调用 LLM 获取回复
5. 对话不持久化到会话历史，仅用于测试

### 验收标准
- [ ] 可使用智能体当前配置发送测试消息并收到回复
- [ ] 修改 base_instructions 后测试使用最新配置
- [ ] 测试对话不保存到会话历史
- [ ] 智能体禁用时测试面板提示不可用

---

## REQ-agent-management-技能绑定

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
用户可为智能体绑定或解绑技能（Skill），绑定后的技能在智能体执行时自动注入到系统提示词中。技能绑定关系在智能体卡片上以数量徽标展示。

### 前置条件
- 智能体已创建
- 系统中存在已创建的技能

### 输入
- 智能体 ID
- 绑定的技能 ID 列表（JSON 数组）

### 输出
- 更新后的智能体 bound_skills 字段
- 操作结果

### 处理规则
1. 绑定操作为全量替换：提交的技能 ID 列表直接覆盖 bound_skills 字段
2. 绑定的技能 ID 必须在 askbi_skills 表中存在，不存在的 ID 被忽略
3. 技能绑定不影响技能自身的 is_active 状态
4. 解绑所有技能时 bound_skills 设为空数组 `[]`

### 验收标准
- [ ] 可为智能体绑定多个技能
- [ ] 可解绑智能体的部分或全部技能
- [ ] 绑定不存在的技能 ID 被忽略不报错
- [ ] 智能体卡片正确显示绑定技能数量
- [ ] 绑定的技能在智能体执行时被正确注入
