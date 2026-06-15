# AskBI Professional Frontend (client_sp)

本项目是原 `client` 文件夹的完全替代版本，采用了现代化的 **Vite + React + Tailwind CSS** 架构。

## 项目优势
- **模块化**：组件、逻辑、API 服务、工具类完全解耦。
- **高性能**：利用 Vite 的极速热更新和构建能力。
- **可维护性**：清晰的代码结构，便于团队协作和功能扩展。
- **专业化**：遵循现代前端开发最佳实践。
- **完全兼容**：所有功能与原 `client` 文件夹完全一致，可直接替代使用。

## 目录结构
- `src/components`: UI 组件（ECharts, 消息项, 思考过程等）。
- `src/services`: 封装后端 API 调用。
- `src/utils`: 工具类（流式渲染管理器等）。
- `src/App.jsx`: 主应用状态与业务逻辑。
- `index.html`: 入口 HTML。
- `vite.config.js`: 开发服务器与代理配置。
- `proxy_server.py`: FastAPI 代理服务器（与原 client 文件夹功能一致）。
- `start_askbi.bat`: 一键启动脚本（自动构建并启动代理服务器）。

## 如何运行

### 方式一：使用启动脚本（推荐，生产模式）
1. 确保已安装 Python 和 Node.js。
2. 双击运行 `start_askbi.bat`，脚本会自动：
   - 安装 Python 依赖（fastapi, uvicorn, httpx, python-multipart）
   - 安装前端依赖（npm install）
   - 构建前端项目（npm run build）
   - 启动代理服务器（python proxy_server.py）
3. 打开浏览器访问：`http://localhost:8000`

### 方式二：开发环境（开发模式）
1. 确保安装了 [Node.js](https://nodejs.org/) 和 Python。
2. 进入 `client_sp` 目录：
   ```bash
   cd client_sp
   ```
3. 安装前端依赖：
   ```bash
   npm install
   ```
4. 启动 Vite 开发服务器：
   ```bash
   npm run dev
   ```
   开发服务器通常运行在 `http://localhost:5173`
   
5. 在另一个终端启动代理服务器：
   ```bash
   pip install fastapi uvicorn httpx python-multipart
   python proxy_server.py
   ```
   
   *注意：开发模式下，Vite 会自动代理 API 请求到 `http://localhost:8000` (proxy_server.py)。*

### 方式三：手动生产部署
1. 构建前端项目：
   ```bash
   npm run build
   ```
2. 启动代理服务器：
   ```bash
   pip install fastapi uvicorn httpx python-multipart
   python proxy_server.py
   ```
3. 打开浏览器访问：`http://localhost:8000`

## 核心逻辑说明
- **StreamingManager**: 独立于 React 生命周期的消息流管理器，确保在切换会话时打字机效果不中断。
- **API Service**: 所有的 `fetch` 请求都封装在 `src/services/api.js` 中，方便统一管理错误和环境切换。
- **Proxy Server**: `proxy_server.py` 提供与原 `client` 文件夹完全相同的 API 代理功能，支持 BI 和 Excel 两种模式。

## 替代原 client 文件夹
本文件夹可以完全替代原 `client` 文件夹使用：
- 所有 API 路由保持一致
- 所有功能保持一致
- 使用方式保持一致（通过 `start_askbi.bat` 或 `proxy_server.py` 启动）
- 配置文件路径保持一致（使用项目根目录的 `config.json`）


