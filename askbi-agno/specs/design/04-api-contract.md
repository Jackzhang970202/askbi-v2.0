# API 契约规范

**版本**: v2.0

---

## 基础规范

| 项目 | 说明 |
|------|------|
| 基础路径 | 无统一前缀，按模块分路由前缀 |
| 认证 | Bearer Token (Authorization: Bearer {token}) |
| 格式 | JSON |
| 跨域 | CORS 允许所有来源 |

## 路由前缀

| 模块 | 前缀 | 入口文件 |
|------|------|----------|
| BI 问数 | (无前缀) | backend/ask/api/bi_api.py |
| Excel 问数 | /excel | backend/ask/api/excel_api.py |
| 技能管理 (新增) | /skills | backend/ask/api/skill_api.py |
| 智能体管理 (新增) | /agents | backend/ask/api/agent_api.py |
| 思考进度流 (新增) | /progress | backend/ask/api/bi_api.py (SSE) |
| 数据源 | (无前缀) | backend/legacy_routes.py |
| 报表 | (无前缀) | backend/legacy_routes.py |
| 大屏 | (无前缀) | backend/legacy_routes.py |
| 认证 | /auth | backend/legacy_routes.py |
| 知识库 | (无前缀) | backend/legacy_routes.py |
| 全局配置 | (无前缀) | backend/legacy_routes.py |

## 响应格式

### 成功响应
```json
{
  "success": true,
  "data": {}
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误信息"
}
```

### 错误状态码
```json
{
  "status": "error",
  "message": "错误信息"
}
```

## HTTP 状态码

| 码 | 说明 |
|----|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未登录/认证失败 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

## API 清单

### BI 问数

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建会话 | POST | /create_chat | 创建 BI 分析会话 |
| 提问 | POST | /ask | 发送自然语言问题 |
| SSE进度流 (新增) | GET | /progress/stream?chatid= | SSE 实时推送任务阶段事件 (替换原轮询) |
| 获取进度 | GET | /progress?chatid= | 获取 BI 任务进度 (兼容保留) |
| 会话列表 | GET | /bi/sessions | 获取 BI 会话列表 |
| 会话消息 | GET | /bi/sessions/{chat_id}/messages | 获取会话消息 |
| 删除会话 | DELETE | /bi/sessions/{chat_id} | 删除会话 |

### Excel 问数

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 上传文件 | POST | /excel/upload_file | 上传 Excel 文件 |
| 提问 | POST | /excel/ask | 发送分析请求 |
| SSE进度流 (新增) | GET | /excel/progress/stream?chatid= | SSE 实时推送任务阶段事件 (替换原轮询) |
| 获取进度 | GET | /excel/progress?chatid= | 获取 Excel 任务进度 (兼容保留) |
| 会话列表 | GET | /excel/list_sessions | 获取 Excel 会话列表 |
| 会话消息 | GET | /excel/sessions/{chat_id}/messages | 获取会话消息 |
| 文件数据 | GET | /excel/get_file_data?chatid= | 获取文件预览数据 |
| 删除会话 | GET | /excel/delete_chat?chatid= | 删除会话 |
| 数据源初始化 | POST | /excel/init_from_datasource | 从数据源初始化 Excel 会话 |
| 健康检查 | GET | /excel/health | Excel 服务健康 |
| 文件下载 | GET | /excel/download_file?chatid=&filename=&is_modified= | 获取文件下载信息 |
| 保存修改文件 | POST | /excel/save_modified_file | 保存修改后的文件 |
| 保存原始文件 | POST | /excel/save_original_file | 保存原始文件 |

### 技能管理 (新增)

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 技能列表 | GET | /skills | 获取技能列表 (支持 ?category= 筛选) |
| 技能详情 | GET | /skills/{skill_id} | 获取技能详情 |
| 创建技能 | POST | /skills | 创建技能 |
| 更新技能 | PUT | /skills/{skill_id} | 更新技能 |
| 删除技能 | DELETE | /skills/{skill_id} | 删除技能 |
| 切换启用 | PATCH | /skills/{skill_id}/toggle | 切换技能启用状态 |
| AI辅助创建 | POST | /skills/ai-generate | AI根据描述生成技能指令 |

### 智能体管理 (新增)

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Agent列表 | GET | /agents | 获取所有Agent配置 |
| Agent详情 | GET | /agents/{agent_name} | 获取单个Agent配置 |
| 更新Agent | PUT | /agents/{agent_name} | 更新Agent配置 |
| 重置Agent | POST | /agents/{agent_name}/reset | 重置为内置默认值 |
| 绑定技能 | PUT | /agents/{agent_name}/skills | 设置Agent绑定的技能列表 |

### SSE 事件格式 (新增)

SSE 推送的事件数据格式:
```
event: stage
data: {"chat_id":"xxx","stage":"sql_generation","status":"running","message":"正在生成SQL...","detail":"SELECT ...","elapsed_ms":1234}

event: stage
data: {"chat_id":"xxx","stage":"sql_generation","status":"done","message":"SQL生成完成","detail":"SELECT ...","elapsed_ms":2345}

event: done
data: {"chat_id":"xxx","message":"所有阶段完成"}
```

阶段类型 (stage):
- `sql_generation` - SQL生成
- `sql_execution` - SQL执行
- `report_generation` - 报告生成
- `chart_generation` - 图表生成
- `code_generation` - 代码生成 (Excel模式)
- `code_execution` - 代码执行 (Excel模式)

### 数据源管理

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 列表 | GET | /datasources | 获取数据源列表 |
| 创建 | POST | /datasources | 添加数据源 |
| 详情 | GET | /datasources/{name} | 获取数据源详情 |
| 删除 | DELETE | /datasources/{name} | 删除数据源 |
| 测试连接 | POST | /datasources/{name}/test | 测试数据源连接 |
| 元数据生成 | POST | /datasources/{name}/generate_metadata | 生成表结构元数据 |
| 表列表 | GET | /datasources/{name}/tables | 获取表列表 |
| 列信息 | GET | /datasources/{name}/tables/{schema}/{table}/columns | 获取列信息 |
| 批量删除 | POST | /datasources/batch_delete | 批量删除数据源 |

### 报表

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 生成报表 | POST | /report/generate | 生成考勤报表 |
| 报表列表 | GET | /report/list | 获取报表列表 |
| 下载报表 | GET | /report/download/{report_id} | 下载报表文件 |
| 删除报表 | DELETE | /report/{report_id} | 删除报表 |
| 重命名报表 | PUT | /report/{report_id}/rename | 重命名报表 |
| 预览数据 | GET | /report/preview/{report_id} | 预览报表数据 |
| 全量数据 | GET | /report/full-data/{report_id} | 获取全量数据 |
| 更新数据 | PUT | /report/update/{report_id} | 更新报表数据 |
| 脱敏切换 | POST | /report/desensitize | 切换脱敏状态 |
| 脱敏预览 | GET | /report/desensitize/preview?report_id= | 脱敏列预览 |
| 报表问数 | POST | /report/ask-question | 基于报表提问 |
| 创建问数会话 | POST | /report/create | 创建报表问数会话 |
| AI 改表 | POST | /report/ai-edit | AI 辅助编辑报表 (占位) |
| ReportRunner 生成 | POST | /reports/generate | 通过 ReportRunner 生成报表 |
| 会话报表下载 | GET | /reports/download/{chat_id}/{filename} | 下载会话报表文件 |
| 会话报表列表 | GET | /reports/list/{chat_id} | 获取会话下的报表列表 |

### 数据大屏

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 生成大屏 | POST | /dashboard/generate | 生成数据大屏 |
| 大屏列表 | GET | /dashboard/list | 获取大屏列表 |
| 静态资源 | GET | /dashboard/static/{dashboard_id}/{path} | 提供大屏静态文件 |
| 截图 | GET | /dashboard/static/{dashboard_id}/screenshot | 大屏截图 |
| 删除大屏 | DELETE | /dashboard/{dashboard_id} | 删除大屏 |

### 用户认证

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 登录 | POST | /auth/login | 用户名密码登录 |
| 登出 | POST | /auth/logout | 退出登录 |
| 当前用户 | GET | /auth/me | 获取当前用户信息 |
| 用户列表 | GET | /auth/users | 获取用户列表 (admin) |
| 创建用户 | POST | /auth/users | 创建用户 (admin) |
| 删除用户 | DELETE | /auth/users/{user_id} | 删除用户 (admin) |
| 修改密码 | PATCH | /auth/users/{user_id}/password | 修改用户密码 (admin) |

### 知识库

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 知识库列表 | GET | /knowledge_bases | 获取知识库列表 |
| 创建知识库 | POST | /knowledge_bases | 添加知识库 |
| 删除知识库 | DELETE | /knowledge_bases/{kb_id} | 删除知识库 |
| 全局知识 | GET | /knowledge/global | 获取全局知识 |
| 保存全局知识 | POST | /knowledge/global | 保存全局知识 |
| 临时知识 | GET | /knowledge/temp/{datasource_name} | 获取数据源临时知识 |
| 保存临时知识 | POST | /knowledge/temp | 保存临时知识 |

### 全局配置

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 配置列表 | GET | /global_configs | 获取全局配置列表 |
| 保存配置 | POST | /global_configs | 创建/更新配置 |
| 删除配置 | DELETE | /global_configs/{config_id} | 删除配置 |
| 切换启用 | PATCH | /global_configs/{config_id}/toggle | 切换启用状态 |

### 其他

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 健康检查 | GET | /health | 服务健康状态 |
| 元数据查看 | GET | /refer/schema?datasource_name= | 查看数据源元数据 |
| 建议问题 | POST | /suggestions | 生成建议问题 |
