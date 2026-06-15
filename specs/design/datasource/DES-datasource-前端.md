# 前端设计文档

**版本**: v1.0
**模块**: 数据源管理 (datasource)
**关联需求**: REQ-datasource

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 数据源管理 | 主页面 / 弹窗 | 列表 + 表单 | REQ-datasource-数据源CRUD |
| 元数据查看 | 弹窗/页面 | SchemaViewer | REQ-datasource-元数据生成 |
| 知识库管理 | 独立页面 | KnowledgeBaseManager | REQ-datasource-知识库 |

---

## 数据源列表页设计

### 页面结构
操作按钮 (添加数据源) → 数据表格 (名称、类型、状态、所有者、创建时间、操作)

### 交互流程
1. 加载数据源列表 (GET /datasources)
2. 点击"添加"打开数据源配置表单
3. 选择数据源类型 (PostgreSQL / MySQL / Excel)
4. 填写连接参数或上传文件
5. 测试连接
6. 保存
7. 列表刷新

### 行操作
- **测试连接**: 点击测试，显示结果
- **生成元数据**: 触发元数据生成
- **查看详情**: 展示完整配置
- **删除**: 确认删除

---

## 元数据查看设计

### 组件: SchemaViewer

### 页面结构
树形结构: Schema → 表 → 列信息 + 样例数据

### 交互流程
1. 选择数据源
2. 加载元数据 (GET /refer/schema?datasource_name=)
3. 展示表列表
4. 展开表查看列信息 (名称、类型、注释)
5. 展示样例数据

### 组件
- **DataSourceConfig**: 数据源配置弹窗，含表单与测试连接
- **SchemaViewer**: 元数据树形展示
- **KnowledgeBaseManager**: 知识库列表管理
- **KnowledgeEditor**: 知识编辑器 (词汇表、参考SQL)

### 接口
- GET /datasources — 数据源列表
- POST /datasources — 创建数据源
- DELETE /datasources/{name} — 删除
- POST /datasources/{name}/test — 测试连接
- POST /datasources/{name}/generate_metadata — 生成元数据
- GET /datasources/{name}/tables — 表列表
- GET /datasources/{name}/tables/{schema}/{table}/columns — 列信息
- GET /refer/schema — 元数据查看
- GET/POST/DELETE /knowledge_bases — 知识库管理
- GET/POST /knowledge/global — 全局知识
- GET/POST /knowledge/temp/{datasource_name} — 临时知识
