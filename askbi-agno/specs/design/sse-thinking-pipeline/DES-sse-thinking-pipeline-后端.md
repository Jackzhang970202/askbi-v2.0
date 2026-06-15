# 后端设计文档

**版本**: v1.0
**模块**: SSE 思考流水线 (sse-thinking-pipeline)
**关联需求**: REQ-sse-thinking-pipeline

---

## 业务流程

### SSE 事件推送流程
工作流执行 → _emit_stage() 调用 → ProgressService.emit_stage_event() → asyncio.Queue.put() → SSE 端点 async generator → StreamingResponse → 前端 fetch 接收

### 阶段事件生命周期
工作流开始 → emit understanding(running) → emit understanding(completed) → emit knowledge_retrieval(running) → ... → emit __done__ → SSE 连接关闭

### 错误处理流程
阶段执行异常 → emit stage(error) + error message → emit __error__ → SSE 连接关闭

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 每个 chatid 独立事件队列 | asyncio.Queue 实例隔离 |
| R002 | 线程安全推送 | loop.call_soon_threadsafe() |
| R003 | 连接断开自动清理 | finally 块清理队列 |
| R004 | 保留轮询端点兼容 | 原有 GET /progress 不删除 |
| R005 | SSE 事件格式统一 | 固定 JSON Schema |
| R006 | 终止事件必须发送 | __done__ 或 __error__ |
| R007 | 阶段状态转换有序 | pending → running → completed/error |

---

## 核心类设计

### ProgressService 重构

现有实现（50 行）使用 in-memory dict 存储进度文本，改为 asyncio.Queue 事件队列。

```python
class ProgressService:
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """服务启动时设置事件循环引用"""
        self._loop = loop
    
    def get_or_create_queue(self, chatid: str) -> asyncio.Queue:
        """获取或创建 chatid 对应的事件队列"""
        if chatid not in self._queues:
            self._queues[chatid] = asyncio.Queue()
        return self._queues[chatid]
    
    def emit_stage_event(self, chatid: str, stage: str, status: str, 
                         message: str, metadata: dict = None):
        """线程安全的阶段事件推送（可在非 async 上下文调用）"""
        event = {
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": int(time.time() * 1000),
            "duration_ms": 0,
            "metadata": metadata or {}
        }
        queue = self.get_or_create_queue(chatid)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(queue.put_nowait, event)
        else:
            queue.put_nowait(event)
    
    async def stream_events(self, chatid: str):
        """async generator，用于 SSE 端点"""
        queue = self.get_or_create_queue(chatid)
        try:
            while True:
                event = await queue.get()
                yield event
                if event["stage"] in ("__done__", "__error__"):
                    break
        finally:
            self._queues.pop(chatid, None)
    
    def cleanup(self, chatid: str):
        """清理指定 chatid 的队列"""
        self._queues.pop(chatid, None)
```

### Workflow 集成

在 bi_workflow.py 和 askexcel_workflow.py 中新增 _emit_stage() 辅助方法：

```python
class BIWorkflow:
    def __init__(self, progress_service: ProgressService, chatid: str):
        self.progress = progress_service
        self.chatid = chatid
        self._stage_start_time: Dict[str, int] = {}
    
    def _emit_stage(self, stage: str, status: str, message: str, metadata: dict = None):
        """工作流内部的阶段事件发射器"""
        if status == "running":
            self._stage_start_time[stage] = int(time.time() * 1000)
        
        duration_ms = 0
        if status in ("completed", "error") and stage in self._stage_start_time:
            duration_ms = int(time.time() * 1000) - self._stage_start_time[stage]
        
        self.progress.emit_stage_event(
            chatid=self.chatid,
            stage=stage,
            status=status,
            message=message,
            metadata=metadata or {}
        )
```

BI 工作流阶段调用示例：
```python
def run(self, question: str):
    # 阶段 1: 意图理解
    self._emit_stage("understanding", "running", "正在理解用户意图...")
    intent = self._llm_understand(question)
    self._emit_stage("understanding", "completed", "意图理解完成", 
                     {"intent": intent})
    
    # 阶段 2: 知识检索
    self._emit_stage("knowledge_retrieval", "running", "正在检索相关知识...")
    knowledge = self._retrieve_knowledge(intent)
    self._emit_stage("knowledge_retrieval", "completed", f"检索到 {len(knowledge)} 条知识",
                     {"knowledge_count": len(knowledge)})
    
    # 阶段 3: SQL 生成
    self._emit_stage("sql_generation", "running", "正在生成 SQL 查询...")
    sql = self._generate_sql(intent, knowledge)
    self._emit_stage("sql_generation", "completed", "SQL 生成完成",
                     {"sql": sql, "db_type": "postgresql"})
    
    # ... 后续阶段
    
    # 终止事件
    self.progress.emit_stage_event(self.chatid, "__done__", "completed", "处理完成")
```

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| BI SSE 流 | GET | `/progress/stream` | REQ-sse-thinking-pipeline-SSE推送 |
| Excel SSE 流 | GET | `/excel/progress/stream` | REQ-sse-thinking-pipeline-SSE推送 |
| 轮询（保留） | GET | `/progress` | 向后兼容 |

### GET /progress/stream

**查询参数**: `chatid`（必填）

**请求头**: `Authorization: Bearer <token>`

**响应**: `text/event-stream`，Content-Type 为 `text/event-stream; charset=utf-8`

**SSE 事件格式**:
```
data: {"stage":"understanding","status":"running","message":"正在理解用户意图...","timestamp":1717891200000,"duration_ms":0,"metadata":{}}

data: {"stage":"understanding","status":"completed","message":"意图理解完成","timestamp":1717891201200,"duration_ms":1200,"metadata":{"intent":"查询本月销售额"}}

data: {"stage":"sql_generation","status":"running","message":"正在生成 SQL 查询...","timestamp":1717891201500,"duration_ms":0,"metadata":{}}

data: {"stage":"sql_generation","status":"completed","message":"SQL 生成完成","timestamp":1717891203500,"duration_ms":2000,"metadata":{"sql":"SELECT SUM(amount) FROM sales WHERE date >= '2026-06-01'","db_type":"postgresql"}}

data: {"stage":"__done__","status":"completed","message":"处理完成","timestamp":1717891210000,"duration_ms":0,"metadata":{}}
```

### GET /excel/progress/stream

**查询参数**: `chatid`（必填）

**请求头**: `Authorization: Bearer <token>`

**响应**: 同上 `text/event-stream` 格式

**Excel 阶段示例**:
```
data: {"stage":"understanding","status":"running","message":"正在分析 Excel 文件...","timestamp":1717891200000,"duration_ms":0,"metadata":{}}

data: {"stage":"code_generation","status":"running","message":"正在生成分析代码...","timestamp":1717891202000,"duration_ms":0,"metadata":{}}

data: {"stage":"__done__","status":"completed","message":"分析完成","timestamp":1717891215000,"duration_ms":0,"metadata":{}}
```

---

## 线程安全设计

工作流可能在非 async 线程执行（如 run_in_executor），需要线程安全：

```python
# 在 backend_api_agno.py 启动时
progress_service = ProgressService()

@app.on_event("startup")
async def startup():
    progress_service.set_loop(asyncio.get_running_loop())

# 在同步工作流中调用
progress_service.emit_stage_event(chatid, "sql_generation", "running", "...")
# 内部自动使用 loop.call_soon_threadsafe() 确保线程安全
```

---

## Proxy Server SSE 代理

在 proxy_server.py 新增 SSE 代理路由，透传后端 SSE 流：

```python
@app.get("/progress/stream")
async def proxy_progress_stream(request: Request, chatid: str):
    """SSE 代理路由，透传后端 SSE 事件流"""
    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{BACKEND_URL}/progress/stream?chatid={chatid}",
                headers={"Authorization": request.headers.get("Authorization", "")}
            ) as response:
                async for line in response.aiter_lines():
                    yield f"{line}\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )
```

---

## 设计约束

1. SSE 使用 fetch + ReadableStream 而非 EventSource，以支持 Bearer Token 认证
2. 保留原有 GET /progress 轮询端点，确保向后兼容
3. ProgressService 单例模式，全局共享
4. 事件队列在 __done__/__error__ 后自动清理
5. 使用 loop.call_soon_threadsafe() 确保跨线程安全
6. SSE 响应禁用缓存（Cache-Control: no-cache）
7. 工作流异常时发送 __error__ 终止事件，不挂起连接
