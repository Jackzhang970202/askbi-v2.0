# AskBI 环境要求

## 方式一：使用已有 conda 环境（推荐）

```bash
conda activate agent-framework
python backend_api_agno.py
```

该环境已包含全部依赖，无需额外安装。

## 方式二：全新环境从零安装

### 1. 创建 Python 环境

```bash
# Python 3.10+ 即可
python -m venv .venv
.venv\Scripts\activate
```

### 2. 安装全部 Python 依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 已包含 **60+ 个包**，覆盖：
- agno, openai — 智能体框架与 LLM 客户端
- fastapi, uvicorn, starlette — Web 服务
- pandas, numpy, openpyxl — 数据处理
- psycopg2-binary — PostgreSQL 驱动
- httpx, requests — HTTP 客户端
- 以及所有传递依赖（pydantic, tiktoken, rich, typer 等）

### 3. 安装 Playwright 浏览器（大屏截图功能需要）

```bash
pip install playwright
playwright install chromium
```

> 如果不使用大屏截图功能，可跳过此步。

### 4. 准备外部服务

| 服务 | 用途 | 必需 |
|------|------|------|
| PostgreSQL | 应用数据库 (askbi_table) + 业务数据库 (jiceng) | 是 |
| 浏览器 (Chrome/Edge) | 大屏截图 (Playwright) | 可选 |

### 5. 启动

```bash
# 初始化数据库表
python create_tables.py

# 启动后端服务 (端口 8002)
python backend_api_agno.py
```

## 依赖分类速查

| 分类 | 核心包 |
|------|--------|
| 智能体框架 | agno, openai |
| Web 服务 | fastapi, uvicorn, starlette |
| 数据处理 | pandas, numpy, openpyxl |
| 数据库 | psycopg2-binary |
| HTTP | httpx, requests |
| 配置 | pydantic, python-dotenv, pyyaml |
