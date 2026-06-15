# 前端设计文档

**版本**: v1.1
**模块**: 记忆管理 (memory-management)
**关联需求**: REQ-memory-management

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 记忆管理页 | `/memory` | 管理页 | REQ-memory-management-管理与可视化 |
| 会话记忆面板 | 聊天页侧栏/弹窗 | 嵌入面板 | REQ-memory-management-会话记忆 |

---

## 记忆管理页设计

### 页面结构
筛选区 → 记忆类型 Tab → 记忆列表 → 详情抽屉 → 操作区

### Tab

| Tab | 数据范围 | 说明 |
|------|----------|------|
| 用户画像 | user | 长期跨会话画像记忆 |
| 会话记忆 | session | 按会话归属的短期记忆 |
| 事件审计 | events | 抽取、跳过、同步、删除等事件 |

### 搜索项

| 字段 | 组件 | 说明 |
|------|------|------|
| 关键词 | Input | 匹配 summary/profile_text |
| 记忆类型 | Select | preference/background/constraint/goal/goal/subject/decision/state |
| 状态 | Select | active/archived/deleted |
| 会话 ID | Input | 仅会话记忆使用 |
| 用户 | Select/Input | 仅 admin/manager 可见 |

### 表格列

| 列名 | 字段 | 操作 |
|------|------|------|
| 摘要 | summary | 点击打开详情 |
| 范围 | memory_scope | user/session |
| 类型 | memory_kind | - |
| 内容 | profile_text | 截断展示 |
| 状态 | status | 状态标签 |
| 更新时间 | updated_at | - |
| 操作 | - | 编辑/归档/删除 |

### 详情抽屉

| 区域 | 内容 |
|------|------|
| 基本信息 | ID、范围、类型、状态、来源会话 |
| 记忆正文 | profile_text 完整内容 |
| 结构化数据 | profile_json JSON 展示 |
| 来源信息 | source_message_ids、source_chat_id |
| mem0 状态 | mem0_id、同步状态 |

### 交互
1. 进入页面自动加载用户画像记忆。
2. 切换 Tab 后加载对应列表。
3. 点击归档/删除需二次确认。
4. 删除后列表即时移除并显示操作反馈。
5. 普通用户不展示用户筛选；管理员可筛选用户。
6. 事件审计只读，不允许编辑。
7. 用户画像记忆可在全局记忆管理页直接编辑 summary/profile_text/memory_kind/status。
8. 会话摘要记忆可在会话记忆面板中直接编辑 summary/profile_text/memory_kind/status。

### 接口
- GET `/memory/user` - 查询用户画像记忆
- GET `/memory/session/{chat_id}` - 查询会话记忆
- GET `/memory/events` - 查询事件审计
- PUT `/memory/{scope}/{id}` - 修改记忆
- PATCH `/memory/{scope}/{id}/archive` - 归档记忆
- DELETE `/memory/{scope}/{id}` - 删除记忆

---

## 会话记忆面板设计

### 展示位置
聊天页顶部上下文区域或右侧弹窗按钮，按钮文案为“会话记忆”。

### 展示内容

| 字段 | 说明 |
|------|------|
| 当前目标 | goal 类型会话记忆 |
| 已确认口径 | decision 类型会话记忆 |
| 当前状态 | state 类型会话记忆 |
| 主题摘要 | subject 类型会话记忆 |

### 交互
1. 打开面板时读取当前 `chat_id` 的会话记忆。
2. 支持手动点击“总结当前会话”。
3. 支持归档某条错误会话记忆。
4. 不在聊天主消息流中强行展示记忆内容。

### 接口
- GET `/memory/session/{chat_id}`
- POST `/memory/session/{chat_id}/summarize`
- PATCH `/memory/session/{id}/archive`

---

## 前端状态设计

| 状态 | 说明 |
|------|------|
| `memoryTab` | 当前 Tab |
| `memoryFilters` | 查询条件 |
| `userMemories` | 用户画像列表 |
| `sessionMemories` | 会话记忆列表 |
| `memoryEvents` | 审计事件列表 |
| `selectedMemory` | 详情抽屉当前记录 |
| `loading` | 列表加载状态 |

---

## 组件规划

| 组件 | 说明 |
|------|------|
| `MemoryManager.jsx` | 记忆管理主页面 |
| `MemoryDetailDrawer.jsx` | 记忆详情抽屉 |
| `SessionMemoryPanel.jsx` | 聊天页会话记忆面板 |
| `MemoryFilters.jsx` | 筛选区 |

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2026-06-15 | 初始版本：定义记忆管理页与会话记忆面板 | zhangqiyuan |

---

**文档结束**
