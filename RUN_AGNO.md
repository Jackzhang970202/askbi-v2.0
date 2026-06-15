# askbi-agno 当前可运行方式

## 后端启动

```bash
python backend_api_agno.py
```

默认端口：`8002`

## 前端代理启动

```bash
python frontend/proxy_server.py
```

默认读取：`config.json -> backend_api_url`

当前已调整为：

```json
{
  "backend_api_url": "http://127.0.0.1:8002"
}
```

## 前端开发启动

```bash
cd frontend
npm install
npm run dev
```

## 当前可用能力

| 能力 | 状态 |
|---|---|
| Excel 上传与问数 | 可用基础链路 |
| Excel 进度/会话/消息 | 可用基础链路 |
| BI 创建会话 | 可用兼容入口 |
| BI 问数 | 兼容占位入口 |
| 非问数功能 | 仍依赖后续继续迁移与联调 |
