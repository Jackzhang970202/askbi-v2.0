# UI/UX 规范

**版本**: v2.0

---

## 设计体系

| 项目 | 内容 |
|------|------|
| UI 框架 | React 18 + TailwindCSS 3.3 |
| 构建工具 | Vite 4.4 |
| 图表库 | Vega-Lite (替换原 ECharts，使用 vega-embed 渲染) |
| 实时通信 | SSE (Server-Sent Events，替换原 HTTP 轮询) |

## 色彩

前端使用 TailwindCSS 默认色板，无自定义品牌色。

### 功能场景
| 类型 | 用途 |
|------|------|
| 主操作 | BI 问数、Excel 问数入口按钮 |
| 成功 | 报表/大屏生成成功提示 |
| 错误 | 请求失败、SQL执行错误 |
| 警告 | 数据异常提醒 |
| 阶段标识 | 思考流程各阶段状态(进行中/完成/失败) |

## 布局

| 区域 | 说明 |
|------|------|
| 侧边栏 | Sidebar 组件，导航菜单(问数/报表/大屏/数据源/用户管理/技能管理/智能体管理) |
| 主内容区 | 聊天式交互界面，消息列表 + 输入框 |
| 登录页 | 独立 LoginPage 组件 |

## 核心页面

| 页面 | 组件 | 说明 |
|------|------|------|
| 问数页 | Sidebar + ChatInput + MessageItem | 支持 BI 模式与 Excel 模式 |
| 数据源管理 | DataSourceConfig | 数据源CRUD、连接测试、元数据生成 |
| 报表管理 | ReportManager + ReportEditor | 报表列表、生成、编辑、脱敏 |
| 大屏管理 | 大屏列表 + 预览 | 大屏生成、预览、下载、截图 |
| 用户管理 | UserManager | 用户CRUD、密码重置 (仅 admin) |
| 知识库管理 | KnowledgeBaseManager + KnowledgeEditor | 数据源知识编辑、词汇表管理 |
| 技能管理 (新增) | SkillManager | 技能CRUD、分类筛选、启用/禁用、指令编辑、AI辅助创建 |
| 智能体管理 (新增) | AgentManager | 6个Agent列表、自定义指令编辑、模型配置、技能绑定 |

## 组件

### 消息展示 (MessageItem)
- 支持用户消息与 AI 回复
- 结构化数据展示 (SQL、图表、执行结果)
- 思考流程展示 (ThinkingPipeline 组件，结构化阶段视图，替换原 ThinkingProcess)
- 图表渲染 (VegaChart 组件，Vega-Lite 声明式 JSON，替换原 EChart)

### 图表渲染 (VegaChart, 新增)
- 接收 Vega-Lite JSON spec 并渲染
- 使用 vega-embed 库
- 支持响应式尺寸
- 替换原 EChart 组件

### 思考流程 (ThinkingPipeline, 新增)
- 结构化阶段卡片视图 (SQL生成→执行→报告→图表)
- 每阶段显示: 标题、状态(进行中/完成/失败)、耗时、详情摘要
- SSE 实时更新阶段状态
- 替换原终端风格 ThinkingProcess 组件

### 技能管理 (SkillManager, 新增)
- 技能列表 (表格形式: 名称/分类/状态/操作)
- 创建/编辑表单 (名称/分类/描述/指令文本区)
- 分类筛选 (sql/chart/report/general)
- 启用/禁用开关
- AI辅助创建按钮

### 智能体管理 (AgentManager, 新增)
- 6个Agent卡片列表 (bi_sql/bi_report/bi_chart/excel_code/excel_report/excel_chart)
- 每个Agent配置面板: 自定义指令(textarea)、模型名称、温度、绑定技能(多选)
- 重置为默认值按钮

### 聊天输入 (ChatInput)
- 文本输入
- 文件上传 (Excel 模式)
- 建议问题推荐 (SuggestionGenerator)

### 模态框 (Modal)
- 数据源配置弹窗
- 报表编辑器弹窗
- 用户管理弹窗

### 错误处理 (ErrorBoundary)
- 组件级错误边界
- 降级显示

## 交互

| 类型 | 说明 |
|------|------|
| SSE 进度推送 | SSE 实时推送任务阶段事件，前端通过 fetch + ReadableStream 消费 |
| 流式响应 | StreamingManager 处理 AI 回复文本流 |
| 加载状态 | LoadingDots 加载动画 |
| 删除确认 | 会话/数据源/报表删除需确认 |
| 阶段动画 | 思考流程各阶段淡入+进度指示 |

## 响应式

| 场景 | 说明 |
|------|------|
| 最小分辨率 | 1366x768 |
| 浏览器 | Chrome / Firefox / Edge / Safari |
| 大屏 | 2560x1440 (大屏预览与截图) |
