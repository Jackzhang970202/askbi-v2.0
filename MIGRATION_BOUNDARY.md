# askbi-agno 复制边界清单

## 目标
在不直接改造 `askBI-renli` 原始目录的前提下，创建新的独立项目 `askbi-agno`。

## 直接复制的核心资产

| 类别 | 来源 | 说明 |
|---|---|---|
| 前端源码 | `askBI-renli/client_sp/` | 作为新项目 `frontend/` 基线 |
| 后端业务源码 | `askBI-renli/` 中除运行时产物外的业务代码 | 作为新项目 `backend/` 基线 |
| 配置文件 | `askBI-renli/config/`、`datasources_config.json`、`config.json`、`docker-compose.yaml` | 后续按新结构修正引用 |
| 静态资源/模板 | `dashboard_preview/`、必要前端静态资源 | 保持原功能 |
| 规格与说明文档 | 仅作为迁移参考，不作为运行资产 |

## 默认不直接复制的运行时产物

| 类别 | 来源 | 说明 |
|---|---|---|
| 日志 | `askBI-renli/**/logs/`、`*.log` | 运行时产物 |
| Python 缓存 | `__pycache__/`、`*.pyc` | 可重新生成 |
| 前端依赖目录 | `client_sp/node_modules/` | 通过安装重新生成 |
| 上传/拆分临时文件 | `askexcel/user_upload_files/`、运行期 split 目录 | 默认不作为核心资产 |
| memories / rag_res 等会话运行结果 | 运行时数据 | 后续确认是否需要迁移 |

## 当前实现约束

| 约束 | 说明 |
|---|---|
| 原始目录保护 | `askBI-renli` 作为稳定基线，不直接做结构重构 |
| 新目录承载 | 后续所有问数框架替换在 `askbi-agno` 中进行 |
| 结构可优化 | 新项目允许调整目录结构，但必须同步修正全部引用 |
