# AskBI 系统部署指南

## 项目概述

AskBI 是一个基于 AI 的智能数据分析系统，提供自然语言查询数据库、生成报表和可视化图表等功能。

## 系统架构

- **前端服务**: 运行在 8000 端口，提供 Web 界面
- **后端 API**: 运行在 8002 端口，处理业务逻辑
- **数据库**: PostgreSQL 数据库（支持双数据库配置）
- **AI 模型**: 通义千问模型
- **RAG 服务**: 集成外部 RAG 知识库检索服务

## 部署前准备

### 1. 环境要求检查

**执行以下命令检查环境：**

```bash
# 检查 Docker 是否安装
docker --version

# 检查 Docker Compose 是否安装
docker-compose --version

# 检查 Python 版本
python --version

# 检查 Node.js 版本（用于 MCP 服务）
node --version
```

### 2. 配置文件准备

**创建数据库配置文件 `config.json`：**

```json
{
    "model": "qwen3-max",
    "api_key": "您的API密钥",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "backend_api_url": "http://askbi-backend:8002",
    "db_config": {
        "host": "172.22.3.237",
        "port": 5432,
        "dbname": "database_metrics",
        "user": "database_metrics",
        "password": "database_metrics_123",
        "database_schema": "jiceng"
    },
    "app_db_config": {
        "host": "localhost",
        "port": 5432,
        "dbname": "askbi_app",
        "user": "askbi_user",
        "password": "askbi_password_123",
        "database_schema": "askbi_table"
    }
}
```

**重要配置说明：**
- `backend_api_url`: 前端服务连接的后端API地址，容器内使用 `http://askbi-backend:8002`
- `db_config`: **业务数据库**配置，用于SQL查询业务数据
- `app_db_config`: **应用数据库**配置，用于存储应用自身的元数据表

**双数据库架构说明：**
- **业务数据库**: 存储业务数据，供MCP服务器进行SQL查询
- **应用数据库**: 存储应用元数据（会话记录、请求日志等），与业务数据隔离

**创建 RAG 服务配置文件 `config_rag.json`：**

```json
{
  "api_url": "http://172.22.4.232/api/v1/retrieval",
  "model": "qwen3-max",
  "headers": {
    "Authorization": "Bearer your-ragflow-token",
    "Content-Type": "application/json"
  },
  "stream": false
}
```

**创建全局规则文件 `knowledge/global_rules.md`：**

```markdown
# AskBI 系统全局规则

## 数据查询规则
1. 所有查询必须包含明确的业务目的
2. 敏感数据查询需要权限审批
3. 查询结果需进行数据脱敏处理

## 报表生成规则
1. 报表标题必须清晰描述内容
2. 图表类型需根据数据类型合理选择
3. 数据源必须明确标注

## 安全规则
1. 禁止执行未经授权的 SQL 语句
2. 查询结果需进行权限验证
3. 所有操作需记录审计日志
```

**创建允许的表列表 `refer_list/allowed_tables.txt`：**

```
# 允许查询的数据表列表
# 每行一个表名，支持通配符

# 示例表名
sales_data
user_profiles
product_catalog
financial_records
```

## 部署步骤

### 步骤 1: 检查并安装依赖包

**执行以下命令检查并安装 Python 依赖：**

```bash
# 检查当前依赖包
pip list | grep -E "(autogen|fastapi|uvicorn|psycopg2)"

# 安装所有依赖
pip install -r requirements.txt
```

### 步骤 2: 构建 Docker 镜像

**检查现有镜像并构建：**

```bash
# 检查是否已有镜像
docker images | grep askbi

# 重新构建镜像
docker-compose build --no-cache

# 或者使用现有镜像（如果有）
docker-compose build
```

### 步骤 3: 确保数据库服务可用

**确保 PostgreSQL 数据库运行：**

```bash
# 检查业务数据库连接
psql -h 172.22.3.237 -p 5432 -U database_metrics -d database_metrics

# 验证业务数据库模式
psql -h 172.22.3.237 -p 5432 -U database_metrics -d database_metrics -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'jiceng';"

# 检查应用数据库连接（部署后）
psql -h localhost -p 5432 -U askbi_user -d askbi_app

# 验证应用数据库模式
psql -h localhost -p 5432 -U askbi_user -d askbi_app -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'askbi_table';"
```

### 步骤 4: 使用 Docker Compose 部署（推荐）

**使用 Docker Compose 一键部署：**

```bash
# 停止现有服务（如果有）
docker-compose down

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

**Docker Compose 服务说明：**
- `askbi-backend`: 后端API服务，包含MCP服务器和业务逻辑
- `askbi-frontend`: 前端代理服务，提供Web界面

**应用数据库自动初始化：**
- 后端服务启动时会自动调用 <mcsymbol name="create_tables" filename="db_utils.py" path="d:\\浪潮\\浪潮工作\\问数\\askDB\\askBI-v1.1_1212\\utils\\db_utils.py" startline="65" type="function"></mcsymbol> 方法
- 自动创建应用元数据表：`askbi_chat_session`, `askbi_general_metadata`, `askbi_request_record`

### 步骤 5: 验证服务状态

**检查后端服务：**

```bash
# 检查后端服务健康状态
curl http://localhost:8002/

# 查看后端服务日志
docker-compose logs askbi-backend
```

**检查前端服务：**

```bash
# 检查前端服务
curl http://localhost:8000

# 在浏览器中访问
open http://localhost:8000
```

## 配置文件说明

### config.json 详细配置

```json
{
    "model": "qwen3-max",                    // AI 模型名称
    "api_key": "your_api_key",               // API 密钥
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", // API 地址
    "backend_api_url": "http://askbi-backend:8002", // 后端API地址（容器内通信）
    "db_config": {
        "host": "172.22.3.237",             // 数据库主机
        "port": 5432,                        // 数据库端口
        "dbname": "database_metrics",        // 数据库名称
        "user": "database_metrics",          // 数据库用户
        "password": "password",              // 数据库密码
        "database_schema": "jiceng"          // 数据库模式
    }
}
```

### config_rag.json 详细配置

```json
{
  "api_url": "http://172.22.4.232/api/v1/retrieval", // RAG 服务地址
  "model": "qwen3-max",                    // 模型名称
  "headers": {
    "Authorization": "Bearer your-token",   // 认证令牌
    "Content-Type": "application/json"      // 内容类型
  },
  "stream": false                           // 是否启用流式响应
}
```

## 依赖包说明

### 核心依赖包

```txt
ag2==0.9.10                    # AI 代理框架
autogen-agentchat==0.7.5       # 自动生成代理聊天
autogen-core==0.7.5            # 自动生成核心库
autogen-ext==0.7.5             # 自动生成扩展库
fastapi==0.104.1               # Web 框架
uvicorn==0.24.0                # ASGI 服务器
psycopg[binary]                # PostgreSQL 驱动
```

### 数据分析和可视化依赖

```txt
pandas==2.3.3                  # 数据分析
numpy==2.3.3                   # 数值计算
matplotlib==3.10.7             # 图表绘制
seaborn==0.13.2                # 统计可视化
plotly==5.24.1                 # 交互式图表
dash==2.18.0                   # Web 应用框架
```

## MCP 服务说明

### MCP 服务器启动流程

系统使用独立的 MCP PostgreSQL 服务器进程：

1. **自动启动**: 后端服务启动时自动启动 MCP 服务器
2. **配置加载**: 从 `config.json` 读取数据库配置
3. **连接管理**: 构建 PostgreSQL 连接字符串
4. **进程管理**: 使用 Node.js 的 `mcp-postgres-server` 包

### MCP 服务特点

- **独立进程**: MCP 服务器作为独立进程运行
- **自动重连**: 支持数据库连接失败时的自动重连
- **配置同步**: 与主配置文件的数据库配置保持同步
- **错误处理**: 完善的错误处理和日志记录

## 常见问题排查

### 问题 1: 容器启动失败

**可能原因：**
- 依赖包缺失
- 配置文件错误
- 数据库连接失败

**解决方案：**

```bash
# 查看容器日志
docker-compose logs askbi-backend

# 进入容器检查
docker exec -it askbi-backend bash

# 检查 Python 环境
python -c "import sys; print(sys.path)"

# 检查依赖包
pip list | grep -E "(ag2|autogen|fastapi)"
```

### 问题 2: 前端无法连接后端

**可能原因：**
- 后端服务未启动
- 网络连接问题
- 端口冲突

**解决方案：**

```bash
# 检查后端服务状态
docker-compose ps askbi-backend

# 检查端口映射
docker port askbi-backend

# 检查容器内网络连通性
docker exec -it askbi-backend curl http://localhost:8002
```

### 问题 3: 数据库连接失败

**解决方案：**

```bash
# 检查数据库服务
psql -h 172.22.3.237 -p 5432 -U database_metrics -d database_metrics

# 检查数据库模式
psql -h 172.22.3.237 -p 5432 -U database_metrics -d database_metrics -c "SELECT current_database(), current_schema();"

# 检查配置文件
cat config.json | grep db_config
```

### 问题 4: MCP 服务启动失败

**解决方案：**

```bash
# 检查 Node.js 环境
docker exec -it askbi-backend node --version

# 检查 MCP 服务进程
docker exec -it askbi-backend ps aux | grep mcp

# 查看 MCP 服务日志
docker-compose logs askbi-backend | grep -i mcp
```

## 维护和监控

### 日常维护命令

```bash
# 查看服务状态
docker-compose ps

# 查看资源使用情况
docker stats

# 查看服务日志
docker-compose logs -f --tail=100

# 备份重要配置文件
cp config.json config.json.backup
cp config_rag.json config_rag.json.backup
```

### 性能优化建议

1. **数据库优化**: 确保数据库有适当的索引
2. **缓存策略**: 考虑实现查询结果缓存
3. **连接池**: 优化数据库连接池配置
4. **资源限制**: 合理设置容器资源限制

## 安全注意事项

1. **API 密钥安全**: 不要将 API 密钥提交到版本控制系统
2. **数据库密码**: 使用强密码并定期更换
3. **网络访问**: 限制外部访问，使用防火墙规则
4. **日志管理**: 定期清理敏感信息的日志
5. **备份策略**: 定期备份重要数据和配置文件

## 故障恢复

### 服务重启流程

```bash
# 1. 停止服务
docker-compose down

# 2. 备份配置文件
cp config.json config.json.backup_$(date +%Y%m%d)
cp config_rag.json config_rag.json.backup_$(date +%Y%m%d)

# 3. 重新启动服务
docker-compose up -d

# 4. 验证服务
docker-compose logs -f --tail=100
```

### 数据恢复流程

```bash
# 如果需要恢复数据库数据，联系DBA进行恢复
# 配置文件可以从备份恢复
cp config.json.backup config.json
cp config_rag.json.backup config_rag.json
```

---

*最后更新: 2024年12月*  
*版本: 1.1*