import uvicorn
from fastapi import FastAPI, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx
import logging
import os
import sys
import json
from pathlib import Path
import asyncio
import requests

# 禁用代理服务器的访问日志，避免 /progress 刷屏
logging.getLogger("uvicorn.access").addFilter(lambda record: "/progress" not in record.getMessage())

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载配置文件
config_path = project_root / "config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# 从配置文件中读取后端API地址（环境变量优先）
REMOTE_BASE_URL = os.environ.get("REMOTE_BASE_URL", config.get("backend_api_url", "http://localhost:8002"))
EXCEL_API_URL = f"{REMOTE_BASE_URL}/excel"

APP_ROOT_PATH = "/askbi"
app = FastAPI(title="AskBI Frontend Proxy", version="1.0.0", root_path=APP_ROOT_PATH)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确定静态文件目录（Vite 构建后的 dist 文件夹）
client_dir = Path(__file__).parent
dist_dir = client_dir / "dist"

# 如果存在 dist 文件夹，挂载静态文件（生产模式）
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")
    app.mount(f"{APP_ROOT_PATH}/assets", StaticFiles(directory=dist_dir / "assets"), name="assets-with-prefix")


async def send_upload_sync(url: str, files, data, headers=None):
    """
    使用同步 requests 发送 multipart，再通过 asyncio.to_thread 调用，
    避开 httpx 在部分环境下的 multipart 同步冲突。
    支持传递认证头。
    """
    def do():
        return requests.post(url, files=files, data=data, headers=headers, timeout=600)
    return await asyncio.to_thread(do)


async def send_form_sync(url: str, data):
    """
    使用同步 requests 发送表单，再通过 asyncio.to_thread 调用，
    避开 AsyncClient 在部分环境下的同步冲突。
    """
    def do():
        return requests.post(url, data=data, timeout=600)
    return await asyncio.to_thread(do)


async def proxy_request(url: str, method: str, request: Request, is_upload: bool = False):
    try:
        content_type = request.headers.get("content-type", "")
        
        # 获取认证头，转发给后端
        auth_headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_headers["Authorization"] = auth_header
        
        # 如果显式指定是上传，或者 Content-Type 是 multipart/form-data，则使用同步上传方式
        if is_upload or "multipart/form-data" in content_type:
            form = await request.form()
            files = []
            data = []
            for key, value in form.multi_items():
                if isinstance(value, (UploadFile, StarletteUploadFile)) or (
                    hasattr(value, "filename") and hasattr(value, "read")
                ):
                    content = await value.read()
                    content_type = value.content_type or "application/octet-stream"
                    files.append((key, (value.filename, content, content_type)))
                else:
                    data.append((key, str(value)))
            response = await send_upload_sync(url, files, data, auth_headers)
        else:
            if method == "POST":
                # 为了解决 AsyncClient 在某些 Linux/Docker 环境下的同步冲突，
                # 对于所有 POST 请求，我们优先使用同步 requests 库进行转发
                if content_type.startswith("application/json"):
                    try:
                        body = await request.json()
                        def do_post():
                            return requests.post(url, json=body, headers=auth_headers, timeout=600)
                        response = await asyncio.to_thread(do_post)
                    except Exception:
                        raw = await request.body()
                        def do_post_raw():
                            return requests.post(url, data=raw, headers=auth_headers, timeout=600)
                        response = await asyncio.to_thread(do_post_raw)
                else:
                    try:
                        form = await request.form()
                        data = [(k, str(v)) for k, v in form.multi_items()]
                        def do_post_form():
                            return requests.post(url, data=data, headers=auth_headers, timeout=600)
                        response = await asyncio.to_thread(do_post_form)
                    except Exception:
                        raw = await request.body()
                        def do_post_raw():
                            return requests.post(url, data=raw, headers=auth_headers, timeout=600)
                        response = await asyncio.to_thread(do_post_raw)
            elif method == "DELETE":
                params = dict(request.query_params)
                def do_delete():
                    return requests.delete(url, params=params, headers=auth_headers, timeout=30)
                response = await asyncio.to_thread(do_delete)
            elif method == "PUT":
                try:
                    body = await request.json()
                    def do_put():
                        return requests.put(url, json=body, headers=auth_headers, timeout=30)
                    response = await asyncio.to_thread(do_put)
                except Exception:
                    raw = await request.body()
                    def do_put_raw():
                        return requests.put(url, data=raw, headers=auth_headers, timeout=30)
                    response = await asyncio.to_thread(do_put_raw)
            elif method == "PATCH":
                try:
                    body = await request.json()
                    def do_patch():
                        return requests.patch(url, json=body, headers=auth_headers, timeout=30)
                    response = await asyncio.to_thread(do_patch)
                except Exception:
                    def do_patch_empty():
                        return requests.patch(url, headers=auth_headers, timeout=30)
                    response = await asyncio.to_thread(do_patch_empty)
            else:
                # GET 请求通常比较稳定，但为了统一，也可以考虑使用 requests
                params = dict(request.query_params)
                def do_get():
                    return requests.get(url, params=params, headers=auth_headers, timeout=30)
                response = await asyncio.to_thread(do_get)

        # 检查响应内容类型
        response_content_type = response.headers.get("content-type", "")
        
        # 如果返回的是 HTML，说明后端可能返回了错误页面
        if response_content_type and "text/html" in response_content_type:
            response_text = response.text
            print(f"[Proxy Warning] {method} {url} returned HTML instead of JSON. Status: {response.status_code}")
            return JSONResponse(content={
                "success": False,
                "error": f"后端 API 返回了 HTML 页面而不是 JSON。可能是后端服务未运行或配置错误。状态码: {response.status_code}",
                "details": f"请求 URL: {url}"
            }, status_code=response.status_code)

        try:
            content = response.json()
        except Exception:
            # 如果无法解析为 JSON，检查是否是 HTML
            response_text = response.text
            if response_text.strip().startswith("<!DOCTYPE") or response_text.strip().startswith("<html"):
                print(f"[Proxy Warning] {method} {url} returned HTML content. Status: {response.status_code}")
                return JSONResponse(content={
                    "success": False,
                    "error": f"后端 API 返回了 HTML 页面而不是 JSON。可能是后端服务未运行或配置错误。状态码: {response.status_code}",
                    "details": f"请求 URL: {url}"
                }, status_code=response.status_code)
            content = response_text

        if response.status_code == 422:
            response_text = response.text
            print(f"[Proxy] 422 Error Detail from {url}: {response_text}")

        return JSONResponse(content=content, status_code=response.status_code)

    except httpx.ConnectError as e:
        print(f"[Proxy Error] 无法连接到后端 API {url}: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"无法连接到后端 API。请检查后端服务是否运行在 {url}",
            "details": str(e)
        }, status_code=503)
    except httpx.TimeoutException as e:
        print(f"[Proxy Error] 请求超时 {method} {url}: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"请求超时。后端 API 响应时间过长。",
            "details": str(e)
        }, status_code=504)
    except Exception as e:
        print(f"[Proxy Error] {method} {url}: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"代理服务器错误: {str(e)}",
            "details": f"请求 URL: {url}"
        }, status_code=500)


# --- BI 路由 ---
@app.post("/upload_file")
async def bi_upload(request: Request):
    print("[Proxy] Forwarding BI upload_file request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/upload_file", "POST", request, True)


@app.post("/ask")
async def bi_ask(request: Request):
    print("[Proxy] Forwarding BI ask request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/ask", "POST", request)


@app.post("/create_chat")
async def bi_create_chat(request: Request):
    print("[Proxy] Forwarding BI create_chat request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/create_chat", "POST", request)


@app.get("/progress")
async def proxy_progress(request: Request):
    params = dict(request.query_params)
    
    def fetch_progress(url, params):
        try:
            resp = requests.get(url, params=params, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    # 优先尝试 BI
    bi_data = await asyncio.to_thread(fetch_progress, f"{REMOTE_BASE_URL}/progress", params)
    if bi_data is not None:
        return JSONResponse(content=bi_data)
        
    # 再尝试 Excel
    excel_data = await asyncio.to_thread(fetch_progress, f"{EXCEL_API_URL}/progress", params)
    if excel_data is not None:
        return JSONResponse(content=excel_data)
        
    return JSONResponse(content=[])


# --- BI Session Routes ---
@app.get("/bi/sessions")
async def proxy_bi_sessions(request: Request):
    print("[Proxy] Forwarding BI sessions list request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/bi/sessions", "GET", request)

@app.get("/bi/sessions/{chat_id}/messages")
async def proxy_get_bi_session_messages(chat_id: str, request: Request):
    print(f"[Proxy] Forwarding get BI session messages request: {chat_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/bi/sessions/{chat_id}/messages", "GET", request)

@app.delete("/bi/sessions/{chat_id}")
async def proxy_delete_bi_session(chat_id: str, request: Request):
    print(f"[Proxy] Forwarding delete BI session request: {chat_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/bi/sessions/{chat_id}", "DELETE", request)


# --- SSE Stream Routes (must use httpx streaming) ---
async def _stream_backend_events(target_url: str, request: Request):
    """转发 SSE 流式响应到前端。"""
    headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    params = dict(request.query_params)

    async with httpx.AsyncClient(timeout=600.0) as client:
        async with client.stream("GET", target_url, headers=headers, params=params) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk


@app.get("/stream")
async def proxy_stream(request: Request):
    """转发 BI SSE 流式响应。"""
    print("[Proxy] Forwarding /stream SSE request...")
    return StreamingResponse(
        _stream_backend_events(f"{REMOTE_BASE_URL}/stream", request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/excel/stream")
async def proxy_excel_stream(request: Request):
    """转发 Excel SSE 流式响应。"""
    print("[Proxy] Forwarding /excel/stream SSE request...")
    return StreamingResponse(
        _stream_backend_events(f"{REMOTE_BASE_URL}/excel/stream", request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/chat/stream")
async def proxy_chat_stream(request: Request):
    """转发 Chat SSE 流式响应。"""
    print("[Proxy] Forwarding /chat/stream SSE request...")
    return StreamingResponse(
        _stream_backend_events(f"{REMOTE_BASE_URL}/chat/stream", request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/chat/general/stream")
async def proxy_general_stream(request: Request):
    """转发 General SSE 流式响应。"""
    print("[Proxy] Forwarding /chat/general/stream SSE request...")
    return StreamingResponse(
        _stream_backend_events(f"{REMOTE_BASE_URL}/chat/general/stream", request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/teams/{team_id}/stream")
async def proxy_team_stream(team_id: str, request: Request):
    """转发 Team SSE 流式响应。"""
    print(f"[Proxy] Forwarding /teams/{team_id}/stream SSE request...")
    return StreamingResponse(
        _stream_backend_events(f"{REMOTE_BASE_URL}/teams/{team_id}/stream", request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# --- Memory Routes ---
@app.api_route("/memory/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_memory(path: str, request: Request):
    print(f"[Proxy] Forwarding /memory/{path} request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/memory/{path}", request.method, request)


# --- Prefixed API Routes for root_path compatibility ---
@app.api_route("/askbi/memory/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_memory_prefixed(path: str, request: Request):
    print(f"[Proxy] Forwarding /askbi/memory/{path} request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/memory/{path}", request.method, request)


# --- Chat Routes (catch-all for all /chat/ paths) ---
@app.api_route("/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_chat(path: str, request: Request):
    """转发 /chat API；单段 /chat/{chat_id} 作为前端 SPA 路由处理。"""
    if request.method == "GET" and "/" not in path:
        print(f"[Proxy] Redirecting unauthenticated SPA route /chat/{path} to app entry")
        return RedirectResponse(url=f"{APP_ROOT_PATH}/", status_code=302)

    target_url = f"{REMOTE_BASE_URL}/chat/{path}"
    print(f"[Proxy] Forwarding /chat/{path} request to backend...")
    return await proxy_request(target_url, request.method, request)


# --- Excel Routes ---
@app.post("/excel/init_from_datasource")
async def proxy_excel_init_from_datasource(request: Request):
    print("[Proxy] Forwarding Excel init_from_datasource request...")
    return await proxy_request(f"{EXCEL_API_URL}/init_from_datasource", "POST", request)


@app.post("/excel/upload_file")
async def proxy_excel_upload(request: Request):
    print("[Proxy] Forwarding Excel upload_file request...")
    return await proxy_request(f"{EXCEL_API_URL}/upload_file", "POST", request, True)


@app.post("/excel/ask")
async def proxy_excel_ask(request: Request):
    print("[Proxy] Forwarding Excel ask request...")
    return await proxy_request(f"{EXCEL_API_URL}/ask", "POST", request)


@app.get("/excel/progress")
async def proxy_excel_progress(request: Request):
    return await proxy_request(f"{EXCEL_API_URL}/progress", "GET", request)


@app.get("/excel/list_sessions")
async def proxy_excel_list_sessions(request: Request):
    print("[Proxy] Forwarding Excel list_sessions request...")
    return await proxy_request(f"{EXCEL_API_URL}/list_sessions", "GET", request)

@app.get("/excel/sessions/{chat_id}/messages")
async def proxy_get_excel_session_messages(chat_id: str, request: Request):
    print(f"[Proxy] Forwarding get Excel session messages request: {chat_id}")
    return await proxy_request(f"{EXCEL_API_URL}/sessions/{chat_id}/messages", "GET", request)

@app.get("/excel/get_file_data")
async def proxy_excel_get_file_data(request: Request):
    print("[Proxy] Forwarding Excel get_file_data request...")
    return await proxy_request(f"{EXCEL_API_URL}/get_file_data", "GET", request)


@app.post("/excel/save_modified_file")
async def proxy_excel_save_modified_file(request: Request):
    print("[Proxy] Forwarding Excel save_modified_file request...")
    return await proxy_request(f"{EXCEL_API_URL}/save_modified_file", "POST", request, True)

@app.post("/excel/save_original_file")
async def proxy_excel_save_original_file(request: Request):
    print("[Proxy] Forwarding Excel save_original_file request...")
    return await proxy_request(f"{EXCEL_API_URL}/save_original_file", "POST", request, True)

# 增加了删除chat对应文件夹的功能！
@app.delete("/excel/delete_chat")
async def proxy_excel_delete_chat(request: Request):
    print("[Proxy] Forwarding Excel delete_chat request...")
    return await proxy_request(f"{EXCEL_API_URL}/delete_chat", "DELETE", request)


@app.get("/excel/download_file")
async def proxy_excel_download_file(request: Request):
    print("[Proxy] Forwarding Excel download_file request...")
    return await proxy_request(f"{EXCEL_API_URL}/download_file", "GET", request)


# --- 数据源配置路由 ---
@app.get("/refer/schema")
async def proxy_get_refer_schema(request: Request):
    """转发到后端 API 获取 refer schema"""
    print("[Proxy] Forwarding refer schema request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/refer/schema", "GET", request)

@app.get("/datasources")
async def proxy_list_datasources(request: Request):
    print("[Proxy] Forwarding datasources list request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources", "GET", request)

@app.post("/datasources")
async def proxy_add_datasource(request: Request):
    print("[Proxy] Forwarding add datasource request...")
    content_type = request.headers.get("content-type", "")
    is_upload = "multipart/form-data" in content_type
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources", "POST", request, is_upload)

@app.get("/datasources/{name}")
async def proxy_get_datasource(name: str, request: Request):
    print(f"[Proxy] Forwarding get datasource request: {name}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}", "GET", request)

@app.delete("/datasources/{name}")
async def proxy_delete_datasource(name: str, request: Request):
    print(f"[Proxy] Forwarding delete datasource request: {name}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}", "DELETE", request)

@app.post("/datasources/{name}/test")
async def proxy_test_datasource(name: str, request: Request):
    print(f"[Proxy] Forwarding test datasource request: {name}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}/test", "POST", request)

@app.get("/datasources/{name}/tables")
async def proxy_get_datasource_tables(name: str, request: Request):
    print(f"[Proxy] Forwarding get datasource tables request: {name}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}/tables", "GET", request)

@app.get("/datasources/{name}/tables/{schema}/{table}/columns")
async def proxy_get_table_columns(name: str, schema: str, table: str, request: Request):
    print(f"[Proxy] Forwarding get table columns request: {name}/{schema}/{table}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}/tables/{schema}/{table}/columns", "GET", request)

@app.post("/datasources/{name}/generate_metadata")
async def proxy_generate_metadata(name: str, request: Request):
    print(f"[Proxy] Forwarding generate metadata request for datasource: {name}")
    return await proxy_request(f"{REMOTE_BASE_URL}/datasources/{name}/generate_metadata", "POST", request)


# --- 知识库路由 ---
@app.get("/knowledge/global")
@app.get("/knowledge/global/")
async def proxy_get_global_knowledge(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge/global", "GET", request)

@app.post("/knowledge/global")
@app.post("/knowledge/global/")
async def proxy_save_global_knowledge(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge/global", "POST", request)

@app.get("/knowledge/temp/{name}")
async def proxy_get_temp_knowledge(name: str, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge/temp/{name}", "GET", request)

@app.post("/knowledge/temp")
@app.post("/knowledge/temp/")
async def proxy_save_temp_knowledge(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge/temp", "POST", request)

@app.get("/knowledge_bases")
@app.get("/knowledge_bases/")
async def proxy_list_knowledge_bases(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge_bases", "GET", request)

@app.post("/knowledge_bases")
@app.post("/knowledge_bases/")
async def proxy_add_knowledge_base(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge_bases", "POST", request)

@app.delete("/knowledge_bases/{id}")
async def proxy_delete_knowledge_base(id: str, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/knowledge_bases/{id}", "DELETE", request)

# --- 全局配置路由 ---
@app.get("/global_configs")
async def proxy_list_global_configs(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/global_configs", "GET", request)

@app.post("/global_configs")
async def proxy_save_global_config(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/global_configs", "POST", request)

@app.delete("/global_configs/{config_id}")
async def proxy_delete_global_config(config_id: int, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/global_configs/{config_id}", "DELETE", request)

@app.patch("/global_configs/{config_id}/toggle")
async def proxy_toggle_global_config(config_id: int, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/global_configs/{config_id}/toggle", "PATCH", request)

# --- 报表生成路由 ---
@app.post("/reports/generate")
async def proxy_reports_generate(request: Request):
    """生成报表"""
    print("[Proxy] Forwarding reports/generate request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/reports/generate", "POST", request)


@app.get("/reports/download/{chat_id}/{filename}")
async def proxy_reports_download(chat_id: str, filename: str, request: Request):
    """下载报表文件"""
    try:
        print(f"[Proxy] Forwarding reports/download request: {chat_id}/{filename}")

        # 获取认证头，转发给后端
        auth_headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_headers["Authorization"] = auth_header

        # 使用 token 查询参数作为备用认证方式
        token = request.query_params.get("token")
        print(f"[Proxy] Token from URL params: {token[:20] if token else 'None'}...")

        if token:
            auth_headers["Authorization"] = f"Bearer {token}"
            print(f"[Proxy] Using token for authentication")

        # 构建后端 URL（包含 token 参数）
        if token:
            backend_url = f"{REMOTE_BASE_URL}/reports/download/{chat_id}/{filename}?token={token}"
            print(f"[Proxy] Backend URL with token: {backend_url[:100]}...")
        else:
            backend_url = f"{REMOTE_BASE_URL}/reports/download/{chat_id}/{filename}"
            print(f"[Proxy] Backend URL without token: {backend_url[:100]}...")

        # 使用同步 requests 下载文件
        def do_download():
            return requests.get(backend_url, headers=auth_headers, timeout=30, stream=True)

        response = await asyncio.to_thread(do_download)

        # 检查响应状态
        if response.status_code != 200:
            try:
                error_data = response.json()
                return JSONResponse(content=error_data, status_code=response.status_code)
            except:
                return JSONResponse(content={
                    "success": False,
                    "error": f"下载失败，状态码: {response.status_code}"
                }, status_code=response.status_code)

        # 返回文件响应
        from fastapi.responses import StreamingResponse

        def iterfile():
            yield from response.iter_content(chunk_size=8192)

        return StreamingResponse(
            iterfile(),
            media_type=response.headers.get("content-type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            headers={
                "Content-Disposition": response.headers.get("Content-Disposition", f'attachment; filename="{filename}"')
            }
        )
    except Exception as e:
        print(f"[Proxy Error] 报表下载失败: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"代理服务器错误: {str(e)}"
        }, status_code=500)


@app.get("/reports/list/{chat_id}")
async def proxy_reports_list(chat_id: str, request: Request):
    """获取报表列表"""
    print(f"[Proxy] Forwarding reports/list request: {chat_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/reports/list/{chat_id}", "GET", request)


# --- 报表管理路由 ---
@app.post("/report/generate")
async def proxy_report_generate(request: Request):
    """生成报表"""
    print("[Proxy] Forwarding report/generate request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/generate", "POST", request, True)


@app.post("/report/create")
async def proxy_report_create(request: Request):
    """创建报表"""
    print("[Proxy] Forwarding report/create request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/create", "POST", request, True)


@app.get("/report/list")
async def proxy_report_list(request: Request):
    """获取用户报表列表"""
    print("[Proxy] Forwarding report/list request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/list", "GET", request)


@app.get("/report/full-data/{report_id}")
async def proxy_report_full_data(report_id: str, request: Request):
    """获取报表完整数据"""
    print(f"[Proxy] Forwarding report/full-data request: {report_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/full-data/{report_id}", "GET", request)


@app.get("/report/preview/{report_id}")
async def proxy_report_preview(report_id: str, request: Request):
    """预览报表"""
    print(f"[Proxy] Forwarding report/preview request: {report_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/preview/{report_id}", "GET", request)


@app.get("/report/download/{report_id}")
async def proxy_report_download(report_id: str, request: Request):
    """下载报表文件"""
    try:
        print(f"[Proxy] Forwarding report/download request: {report_id}")

        # 获取认证头
        auth_headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_headers["Authorization"] = auth_header

        # 使用 token 查询参数作为备用认证方式
        token = request.query_params.get("token")
        desensitized = request.query_params.get("desensitized", "false")

        if token:
            auth_headers["Authorization"] = f"Bearer {token}"

        # 构建后端 URL
        backend_url = f"{REMOTE_BASE_URL}/report/download/{report_id}?desensitized={desensitized}"
        if token:
            backend_url += f"&token={token}"

        # 使用同步 requests 下载文件
        def do_download():
            return requests.get(backend_url, headers=auth_headers, timeout=60, stream=True)

        response = await asyncio.to_thread(do_download)

        # 检查响应状态
        if response.status_code != 200:
            try:
                error_data = response.json()
                return JSONResponse(content=error_data, status_code=response.status_code)
            except:
                return JSONResponse(content={
                    "success": False,
                    "error": f"下载失败，状态码: {response.status_code}"
                }, status_code=response.status_code)

        # 返回文件响应
        from fastapi.responses import StreamingResponse
        from urllib.parse import quote

        # 获取文件名
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = "报表.xlsx"
        if "filename=" in content_disposition:
            import re
            match = re.search(r'filename[*]?=["\']?([^"\';\n]+)["\']?', content_disposition)
            if match:
                filename = match.group(1)

        # 对中文文件名进行 URL 编码 (RFC 5987)
        encoded_filename = quote(filename, safe='')

        def iterfile():
            yield from response.iter_content(chunk_size=8192)

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        print(f"[Proxy Error] 报表下载失败: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"代理服务器错误: {str(e)}"
        }, status_code=500)


@app.post("/report/ask")
async def proxy_report_ask(request: Request):
    """报表问数"""
    print("[Proxy] Forwarding report/ask request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/ask", "POST", request)


@app.post("/report/ai-edit")
async def proxy_report_ai_edit(request: Request):
    """AI改表"""
    print("[Proxy] Forwarding report/ai-edit request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/ai-edit", "POST", request)


@app.post("/report/desensitize")
async def proxy_report_desensitize(request: Request):
    """脱敏设置"""
    print("[Proxy] Forwarding report/desensitize request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/desensitize", "POST", request)


@app.get("/report/desensitize/methods")
async def proxy_report_desensitize_methods(request: Request):
    """获取脱敏方法"""
    print("[Proxy] Forwarding report/desensitize/methods request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/desensitize/methods", "GET", request)


@app.get("/report/desensitize/preview")
async def proxy_report_desensitize_preview(request: Request):
    """预览脱敏效果"""
    print("[Proxy] Forwarding report/desensitize/preview request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/desensitize/preview", "GET", request)


@app.delete("/report/{report_id}")
async def proxy_report_delete(report_id: str, request: Request):
    """删除报表"""
    print(f"[Proxy] Forwarding report/delete request: {report_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/{report_id}", "DELETE", request)


@app.get("/report/download-info/{report_id}")
async def proxy_report_download_info(report_id: str, request: Request):
    """获取报表下载信息"""
    print(f"[Proxy] Forwarding report/download-info request: {report_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/download-info/{report_id}", "GET", request)


@app.post("/report/ask-question")
async def proxy_report_ask_question(request: Request):
    """报表问数提问"""
    print("[Proxy] Forwarding report/ask-question request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/ask-question", "POST", request)


@app.put("/report/update/{report_id}")
async def proxy_report_update(report_id: str, request: Request):
    """更新报表数据"""
    print(f"[Proxy] Forwarding report/update request: {report_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/report/update/{report_id}", "PUT", request)


# --- 大屏管理路由 ---
@app.post("/dashboard/generate")
async def proxy_dashboard_generate(request: Request):
    """生成大屏"""
    print("[Proxy] Forwarding dashboard/generate request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/dashboard/generate", "POST", request, True)


@app.get("/dashboard/list")
async def proxy_dashboard_list(request: Request):
    """获取大屏列表"""
    print("[Proxy] Forwarding dashboard/list request...")
    return await proxy_request(f"{REMOTE_BASE_URL}/dashboard/list", "GET", request)


@app.delete("/dashboard/{dashboard_id}")
async def proxy_dashboard_delete(dashboard_id: str, request: Request):
    """删除大屏"""
    print(f"[Proxy] Forwarding dashboard/delete request: {dashboard_id}")
    return await proxy_request(f"{REMOTE_BASE_URL}/dashboard/{dashboard_id}", "DELETE", request)


@app.get("/dashboard/static/{dashboard_id}/{path:path}")
async def proxy_dashboard_static(dashboard_id: str, path: str, request: Request):
    """大屏静态文件代理"""
    try:
        print(f"[Proxy] Forwarding dashboard/static request: {dashboard_id}/{path}")

        # 构建后端 URL
        backend_url = f"{REMOTE_BASE_URL}/dashboard/static/{dashboard_id}/{path}"

        # 获取认证头
        auth_headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_headers["Authorization"] = auth_header

        # 使用同步 requests 获取文件
        def do_fetch():
            return requests.get(backend_url, headers=auth_headers, timeout=30, stream=True)

        response = await asyncio.to_thread(do_fetch)

        # 检查响应状态
        if response.status_code != 200:
            try:
                error_data = response.json()
                return JSONResponse(content=error_data, status_code=response.status_code)
            except:
                return JSONResponse(content={
                    "success": False,
                    "error": f"获取文件失败，状态码: {response.status_code}"
                }, status_code=response.status_code)

        # 返回文件响应
        from fastapi.responses import StreamingResponse
        import mimetypes

        # 猜测 MIME 类型
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = response.headers.get("content-type", "application/octet-stream")

        def iterfile():
            yield from response.iter_content(chunk_size=8192)

        return StreamingResponse(
            iterfile(),
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        print(f"[Proxy Error] 大屏静态文件代理失败: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"代理服务器错误: {str(e)}"
        }, status_code=500)


# --- 认证路由 ---
@app.post("/auth/login")
async def proxy_auth_login(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/login", "POST", request)

@app.post("/auth/logout")
async def proxy_auth_logout(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/logout", "POST", request)

@app.get("/auth/me")
async def proxy_auth_me(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/me", "GET", request)

@app.get("/auth/users")
async def proxy_auth_list_users(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/users", "GET", request)

@app.post("/auth/users")
async def proxy_auth_create_user(request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/users", "POST", request)

@app.delete("/auth/users/{user_id}")
async def proxy_auth_delete_user(user_id: int, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/users/{user_id}", "DELETE", request)

@app.patch("/auth/users/{user_id}/password")
async def proxy_auth_update_password(user_id: int, request: Request):
    return await proxy_request(f"{REMOTE_BASE_URL}/auth/users/{user_id}/password", "PATCH", request)


# --- 静态文件服务（必须在所有 API 路由之后）---
@app.get("/")
async def read_root():
    # 优先使用构建后的 index.html（生产模式）
    dist_index = dist_dir / "index.html"
    if dist_index.exists():
        with open(dist_index, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    
    # 如果不存在 dist，返回开发模式的提示
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AskBI - 开发模式</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>AskBI 开发模式</h1>
        <p>请先运行 <code>npm run build</code> 构建项目，或使用 <code>npm run dev</code> 启动开发服务器。</p>
        <p>开发服务器通常运行在 <a href="http://localhost:5173">http://localhost:5173</a></p>
    </body>
    </html>
    """)

# 处理所有静态资源请求（用于 Vite 构建后的文件，SPA 路由回退）
# 注意：这个路由必须在所有 API 路由之后定义，否则会覆盖 API 路由
@app.get("/{path:path}")
async def serve_static(path: str, request: Request):
    full_path = str(request.url.path)
    match_path = full_path
    if match_path.startswith(APP_ROOT_PATH):
        match_path = match_path[len(APP_ROOT_PATH):] or "/"
    api_paths = [
        "/upload_file", "/ask", "/create_chat", "/progress",
        "/excel/", "/bi/", "/datasources", "/refer/schema", "/knowledge", "/knowledge_bases",
        "/global_configs", "/auth/", "/reports/", "/report/", "/dashboard/",
        "/skills/", "/agents/", "/teams/", "/memory/",
    ]

    if match_path.startswith("/memory/"):
        print(f"[Proxy Fallback] Forwarding memory API from catch-all: {full_path}")
        return await proxy_request(f"{REMOTE_BASE_URL}{match_path}", request.method, request)

    if any(match_path.startswith(api_path) for api_path in api_paths):
        print(f"[Proxy ERROR] API path '{full_path}' was caught by catch-all route!")
        print(f"[Proxy ERROR] This means the specific route was not matched. Check route order!")
        return JSONResponse(content={
            "success": False,
            "error": f"API route '{full_path}' was not properly matched. This is a routing issue."
        }, status_code=500)
    
    # 只有非 API 路径才会继续到这里
    print(f"[Proxy] Static file request for path: {path}, full_path: {full_path}")
    
    # 尝试从 dist 目录提供文件
    if dist_dir.exists():
        file_path = dist_dir / path
        # 确保路径在 dist_dir 内（防止路径遍历攻击）
        try:
            file_path.resolve().relative_to(dist_dir.resolve())
        except ValueError:
            return JSONResponse(content={"error": "Invalid path"}, status_code=400)
        
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # 如果文件不存在，返回 index.html（用于 SPA 路由）
        # 注意：这只会对非 API 路径执行
        dist_index = dist_dir / "index.html"
        if dist_index.exists():
            with open(dist_index, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    
    return JSONResponse(content={"error": "Not found"}, status_code=404)


async def check_backend_health():
    """检查后端 API 是否可访问"""
    try:
        def do_check():
            return requests.get(f"{REMOTE_BASE_URL}/", timeout=5.0)
        response = await asyncio.to_thread(do_check)
        if response.status_code == 200:
            try:
                data = response.json()
                return True, "后端 API 连接正常"
            except:
                return False, f"后端 API 返回了非 JSON 响应。请检查 {REMOTE_BASE_URL} 是否正确"
        else:
            return False, f"后端 API 返回状态码 {response.status_code}"
    except Exception as e:
        return False, f"检查后端 API 时出错: {str(e)}"

if __name__ == "__main__":
    print("=" * 50)
    print("本地代理服务器启动中...")
    print("请访问: http://localhost:8000")
    print(f"后端目标: {REMOTE_BASE_URL}")
    if dist_dir.exists():
        print("模式: 生产模式 (使用 dist 文件夹)")
    else:
        print("模式: 开发模式 (请先运行 npm run build 或使用 Vite dev server)")
    
    # 检查后端 API 连接
    print("\n正在检查后端 API 连接...")
    import asyncio
    is_healthy, message = asyncio.run(check_backend_health())
    if is_healthy:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        print("\n警告: 后端 API 不可用，某些功能可能无法正常工作。")
        print("=" * 50)
    
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)

