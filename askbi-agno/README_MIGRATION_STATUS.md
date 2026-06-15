# askbi-agno 当前迁移状态

| 项目 | 状态 |
|---|---|
| 新目录已建立 | 是 |
| 前端已复制到 `frontend/` | 是 |
| 原项目基线已复制 | 是 |
| Excel Agno 工作流已接入 | 是 |
| Excel 兼容接口已接入 | 是 |
| BI 兼容接口已接入 | 是，当前为兼容占位实现 |
| 非问数模块保持基线复制 | 是 |
| 全量等价联调 | 否 |
| BI 完整 Agno 工作流 | 否 |

## 当前启动入口

| 入口 | 路径 | 说明 |
|---|---|---|
| 后端 | `backend_api_agno.py` | 新 Agno 迁移后端入口 |
| 前端代理 | `frontend/proxy_server.py` | 原前端代理基线 |
| 前端源码 | `frontend/src/` | 原前端源码 |

## 当前已兼容接口

| 接口 | 状态 |
|---|---|
| `/excel/upload_file` | 已接入 |
| `/excel/ask` | 已接入 |
| `/excel/progress` | 已接入 |
| `/excel/list_sessions` | 已接入 |
| `/excel/sessions/{chat_id}/messages` | 已接入 |
| `/create_chat` | 已接入 |
| `/ask` | 已接入，占位兼容 |
| `/progress` | 已接入，占位兼容 |
| `/bi/sessions` | 已接入，占位兼容 |
| `/bi/sessions/{chat_id}/messages` | 已接入，占位兼容 |
| `/bi/sessions/{chat_id}` | 已接入，占位兼容 |

## 剩余关键工作

| 工作 | 说明 |
|---|---|
| BI 完整 Agno 工作流替换 | 需要替换当前 BI 占位兼容实现 |
| 引用/配置全量收口 | 需要继续清理旧路径与旧依赖 |
| 非问数功能逐项验证 | 报表、大屏、数据源配置还需联调 |
| 前后端完整联调 | 还未完成 |
