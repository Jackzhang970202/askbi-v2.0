# AskBI 项目协作入口

## 项目定位

AskBI 是一个企业级智能 BI 问数平台，基于 Agno 多智能体框架，支持数据库自然语言问数、Excel 文件智能分析、报表生成与数据大屏生成。

## 当前已确认事实

| 项目 | 内容 |
|---|---|
| 后端服务 | FastAPI (端口 8002) |
| 智能体框架 | Agno (Agent / Workflow) |
| 模型接入 | OpenAI 兼容 API |
| 默认模型 | config.json 中的 model 字段 (当前 qwen3.5-flash) |
| 前端框架 | React 18 + Vite + TailwindCSS |
| 数据库 | PostgreSQL (双 Schema: jiceng 业务库 + askbi_table 应用库) |
| 数据源类型 | PostgreSQL / MySQL / Excel |
| 数据源配置 | datasources_config.json + DB |
| 认证方式 | Bearer Token + TOKEN_CACHE 内存缓存 |
| 用户角色 | admin / manager / user |
| 图表库 | ECharts |
| 报表类型 | 人事考勤 / 部门维度 / 多月个人 / 多月部门 |
| 大屏模板 | dashboard_preview/style4_business_cyan |
| 核心入口 | backend_api_agno.py |
| 配置文件 | config.json |
| 元数据存储 | DB (askbi_chat_knowledge) + 文件 (refer/) |
| 会话存储 | PostgreSQL (askbi_chat_session / askbi_messages) |

## 协作规则

| 规则 | 说明 |
|---|---|
| 以代码为准 | 所有文档必须以当前仓库真实代码状态为准，不得主观补充未确认的技术栈或模块 |
| 不补全未知事实 | 未确认的前端组件、数据库业务表、部署方案不得主观补充 |
| 模块文档独立 | 每个模块的 REQ/DES/TASK/CHK 独立存放于 specs/{模块}/ 下 |
| 变更及时回写 | 模块级变更后同步更新对应模块文档 |

## ZSSpec 技能优先级

| 场景 | 优先命令 |
|---|---|
| 需求讨论 / 范围澄清 | /zsspec-brain |
| 生成或更新模块 spec | /zsspec-spec |
| 开发准入并开始实现 | /zsspec-apply |
| 开发中变更 / 修正 | /zsspec-change |
| 完成验收 / 状态同步 | /zsspec-done |

## 命令速查

| 命令 | 用途 |
|---|---|
| `conda activate agent-framework` | 激活 conda 环境 |
| `python backend_api_agno.py` | 启动后端服务 |
| `cd frontend && npm run dev` | 启动前端开发服务器 |
| `pip install -r requirements.txt` | 安装依赖（非 conda 环境） |
| `playwright install chromium` | 安装大屏截图浏览器 |

## 环境说明

详见 `ENVIRONMENT.md`。使用 `agent-framework` conda 环境可完美运行，无需额外安装。
