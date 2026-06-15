# 架构设计

**版本**: v2.0

---

## 系统概述

| 项目 | 内容 |
|------|------|
| 系统名称 | AskBI |
| 系统类型 | 智能 BI 问数平台 |
| 目标用户 | 企业数据分析人员、业务用户 |
| 核心价值 | 通过自然语言实现数据库问数、Excel 分析、报表与大屏的自动生成 |

## 业务模块

| 模块 | 职责 | 功能 |
|------|------|------|
| BI 问数 (bi-query) | 数据库自然语言问数 | 自然语言→SQL生成→执行→报告→图表 |
| Excel 问数 (excel-query) | Excel 文件智能分析 | 文件上传→pandas代码生成→执行→报告→图表 |
| 报表生成 (report) | 考勤报表生成与管理 | HR考勤/部门维度/多月个人/多月部门报表生成与脱敏 |
| 数据大屏 (dashboard) | 数据可视化大屏 | 个人+部门维度数据→Vega-Lite大屏生成与截图 |
| 数据源管理 (datasource) | 数据源CRUD与元数据 | 数据源增删改查、连接测试、元数据生成、跨Schema支持 |
| 用户认证 (auth) | 用户认证与权限管理 | 登录/登出、Token认证、RBAC角色控制、用户管理 |
| 技能系统 (skill-system) | 动态提示词注入管理 | 技能CRUD、技能分类、运行时注入Agent系统提示词、AI辅助创建 |
| 智能体管理 (agent-management) | Agent配置化管理 | 6个Agent可配置化(指令/模型/技能绑定)、运行时加载覆盖默认值 |

## 技术栈

**后端**:
| 层级 | 技术 | 版本/说明 |
|------|------|-----------|
| 框架 | FastAPI | 0.100+ |
| 服务器 | uvicorn | 端口 8002 |
| 智能体 | Agno | Agent / Workflow |
| 模型 | OpenAI 兼容 API | 默认 qwen3.5-flash (DashScope) |
| 数据库 | PostgreSQL | psycopg2-binary |
| 数据处理 | pandas | Excel 读写与分析 |
| 实时通信 | SSE | Server-Sent Events (asyncio.Queue + StreamingResponse) |

**前端**:
| 层级 | 技术 | 版本 |
|------|------|------|
| 框架 | React | 18.2 |
| 构建工具 | Vite | 4.4 |
| CSS | TailwindCSS | 3.3 |
| 图表 | Vega-Lite | vega-lite@5 + vega-embed (替换原 ECharts) |
| 实时通信 | SSE | fetch + ReadableStream (替换原 HTTP 轮询) |

## 目录结构

**后端**:
```
askbi-agno/
├── backend_api_agno.py          # FastAPI 入口 (端口 8002)
├── config.json                  # 模型+数据库配置
├── backend/
│   ├── ask/
│   │   ├── agents/              # 6个 Agno Agent (内置默认定义)
│   │   │   ├── bi_sql_agent.py        # SQL 生成 Agent
│   │   │   ├── bi_report_agent.py     # BI 报告 Agent
│   │   │   ├── bi_chart_agent.py      # BI 图表 Agent
│   │   │   ├── askexcel_code_agent.py # Excel 代码生成 Agent
│   │   │   ├── askexcel_report_agent.py # Excel 报告 Agent
│   │   │   └── askexcel_chart_agent.py  # Excel 图表 Agent
│   │   ├── workflows/           # Workflow 编排
│   │   │   ├── bi_workflow.py           # BI 工作流 (含技能注入+SSE推送)
│   │   │   └── askexcel_workflow.py     # Excel 工作流 (含技能注入+SSE推送)
│   │   ├── api/                 # API 路由
│   │   │   ├── bi_api.py              # BI 问数 API
│   │   │   ├── excel_api.py           # Excel 问数 API
│   │   │   ├── skill_api.py           # 技能管理 API (新增)
│   │   │   └── agent_api.py           # 智能体管理 API (新增)
│   │   ├── skills/              # 技能系统 (新增)
│   │   │   ├── skill_manager.py       # 技能CRUD与缓存
│   │   │   └── skill_registry.py      # 技能注入注册表
│   │   ├── agents_config/       # 智能体配置 (新增)
│   │   │   └── agent_manager.py       # Agent配置加载与合并
│   │   └── services/            # 业务服务
│   │       ├── session_service.py       # 会话管理
│   │       └── progress_service.py      # SSE事件流推送 (重构)
│   └── legacy_routes.py         # 历史路由 (数据源/认证/报表/大屏)
├── core/                        # 核心模块
│   ├── report_generator.py            # HR考勤报表生成
│   ├── dept_report_generator.py       # 部门维度报表生成
│   ├── multi_month_report_generator.py # 多月个人报表生成
│   ├── multi_month_dept_report_generator.py # 多月部门报表生成
│   ├── schema_loader.py               # 元数据加载
│   └── session_manager.py             # 会话管理
├── datasources/                 # 数据源层
│   ├── datasource_manager.py          # 数据源管理器
│   ├── pgsql.py                       # PostgreSQL 连接器
│   ├── mysql.py                       # MySQL 连接器
│   ├── excel.py                       # Excel 连接器
│   └── knowledge_manager.py           # 知识库管理
├── config/                      # 配置模块
│   ├── config_db.py                   # 数据库配置 (含技能/Agent表常量)
│   └── config_handler.py              # 模型加载
├── utils/                       # 工具函数
│   ├── db_utils.py                    # 数据库工具 (含技能/Agent DDL+CRUD)
│   ├── pg_db_utils.py                 # PostgreSQL 工具
│   ├── auth_utils.py                  # 认证工具
│   ├── datasource_sql_executor.py     # SQL 执行器
│   ├── schema_generator.py            # 元数据生成器
│   ├── white_list_utils.py            # 白名单工具
│   ├── desensitize.py                 # 脱敏工具
│   └── general_utils.py               # 通用工具
└── prompt.py                    # Vega-Lite 图表生成 Prompt (重构)

```

**前端**:
```
frontend/
├── index.html                   # HTML入口 (Vega-Lite CDN 替换 ECharts CDN)
├── src/
│   ├── main.jsx                 # React 入口
│   ├── index.css                # 全局样式
│   ├── App.jsx                  # 主应用容器 (含技能/Agent路由分发)
│   ├── components/              # 组件
│   │   ├── Sidebar.jsx                # 侧边栏导航 (新增技能/Agent入口)
│   │   ├── ChatInput.jsx              # 聊天输入
│   │   ├── MessageItem.jsx            # 消息展示 (集成VegaChart+ThinkingPipeline)
│   │   ├── LoginPage.jsx              # 登录页
│   │   ├── SchemaViewer.jsx           # 元数据查看器
│   │   ├── DataSourceConfig.jsx       # 数据源配置
│   │   ├── ReportEditor.jsx           # 报表编辑器
│   │   ├── ReportManager.jsx          # 报表管理
│   │   ├── UserManager.jsx            # 用户管理
│   │   ├── KnowledgeBaseManager.jsx   # 知识库管理
│   │   ├── KnowledgeEditor.jsx        # 知识编辑器
│   │   ├── VegaChart.jsx              # Vega-Lite 图表组件 (新增, 替换 EChart)
│   │   ├── ThinkingPipeline.jsx       # 结构化思考流程 (新增, 替换 ThinkingProcess)
│   │   ├── SkillManager.jsx           # 技能管理页面 (新增)
│   │   ├── AgentManager.jsx           # 智能体管理页面 (新增)
│   │   ├── Modal.jsx                  # 模态框
│   │   ├── LoadingDots.jsx            # 加载动画
│   │   ├── ErrorBoundary.jsx          # 错误边界
│   │   └── Icons.jsx                  # 图标组件
│   ├── hooks/                   # 自定义 Hooks (新增)
│   │   └── useProgressStream.js       # SSE 流式进度 Hook
│   ├── services/
│   │   └── api.js               # API 服务层 (新增技能/Agent/SSE方法)
│   └── utils/
│       ├── StreamingManager.js        # 流式请求管理 (新增进度阶段协调)
│       └── modalHelper.js             # 模态框辅助
├── proxy_server.py              # 前端代理服务器 (新增SSE代理路由)
└── package.json                 # 依赖配置
```

## 安全

| 项目 | 方案 |
|------|------|
| 认证 | Bearer Token (内存缓存) |
| 授权 | RBAC (admin / manager / user) |
| 密码存储 | SHA-256 哈希 |
| SQL 安全 | 仅允许 SELECT 查询，检测非查询操作拦截 |
| 数据隔离 | 用户级 owner_id 隔离数据源与报表 |
| 跨域 | CORS 允许所有来源 (开发环境) |

## 部署

| 项目 | 说明 |
|------|------|
| 后端端口 | 8002 |
| 前端代理 | proxy_server.py |
| 数据库 | PostgreSQL (独立服务) |
| 文件存储 | 本地文件系统 (runtime/ report_files/ dashboard_files/ datasources/excel_files/) |
