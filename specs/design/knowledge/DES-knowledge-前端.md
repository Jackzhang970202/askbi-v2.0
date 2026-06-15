# 前端设计文档

**版本**: v1.0
**模块**: 知识库管理 (knowledge)
**关联需求**: REQ-knowledge

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 知识库管理 | 独立页面 | 列表 + 表单 | REQ-knowledge-知识库CRUD |
| 全局知识编辑 | 独立页面 / 弹窗 | 文本编辑器 | REQ-knowledge-全局知识 |
| 数据源知识编辑 | 弹窗 | 表单 (词汇/SQL/文本) | REQ-knowledge-临时知识 |

---

## 知识库管理页设计

### 页面结构
操作按钮 (添加知识库) → 数据表格 (ID, 名称, 类型, API地址, 操作)

### 交互流程
1. 加载知识库列表 (GET /knowledge_bases)
2. 点击"添加"打开表单
3. 填写知识库信息 (id, name, type, api_url, headers)
4. 提交创建
5. 列表刷新

### 行操作
- **编辑**: 修改知识库信息
- **删除**: 确认删除

---

## 全局知识编辑设计

### 组件: KnowledgeEditor

### 页面结构
大文本输入框 → 保存按钮

### 交互流程
1. 加载全局知识 (GET /knowledge/global)
2. 文本框展示内容
3. 编辑后点击保存
4. 提交保存 (POST /knowledge/global)
5. 提示成功

---

## 数据源知识编辑设计

### 组件: KnowledgeEditor

### 页面结构
标签页: 知识文本 / 业务词汇 / 参考SQL
- 知识文本: 大文本输入
- 业务词汇: 标签输入 (可添加/删除)
- 参考SQL: SQL 列表 (每条可编辑)

### 交互流程
1. 选择数据源
2. 加载临时知识 (GET /knowledge/temp/{datasource_name})
3. 展示三个标签页内容
4. 编辑后保存 (POST /knowledge/temp)

### 组件
- **KnowledgeBaseManager**: 知识库列表管理
- **KnowledgeEditor**: 知识编辑器 (全局/临时)

### 接口
- GET/POST/DELETE /knowledge_bases — 知识库 CRUD
- GET/POST /knowledge/global — 全局知识
- GET/POST /knowledge/temp — 临时知识
