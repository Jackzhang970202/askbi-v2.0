from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from backend.ask.services.excel_preprocess import get_file_metadata, parse_range_param, process_file as preprocess_file
from backend.ask.services.progress_service import progress_service
from backend.ask.services.session_service import session_service
from backend.ask.services.memory_service import memory_service
from backend.ask.workflows.askexcel_workflow import askexcel_workflow_impl
from utils.auth_utils import get_current_user, is_admin_or_manager
from utils.db_utils import db_utils
from config.config_db import TABLE_MESSAGES, TABLE_REQUEST_RECORD

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = BASE_DIR / "runtime"
UPLOAD_DIR = RUNTIME_DIR / "excel_uploads"
CHAT_DIR = RUNTIME_DIR / "excel_chats"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHAT_DIR.mkdir(parents=True, exist_ok=True)


def get_chat_path(chatid: str) -> Path:
    chat_path = CHAT_DIR / chatid
    chat_path.mkdir(parents=True, exist_ok=True)
    return chat_path

def list_excel_paths(chatid: str) -> list[str]:
    chat_path = get_chat_path(chatid)
    allowed_suffixes = {".xlsx", ".xls", ".csv", ".json"}
    return [
        str(p)
        for p in chat_path.iterdir()
        if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in allowed_suffixes
    ]


def make_json_safe(value: Any) -> Any:
    try:
        import pandas as pd
    except Exception:
        pd = None

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value:
            return None
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        return value
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    if pd is not None:
        if isinstance(value, pd.DataFrame):
            return make_json_safe(value.where(pd.notna(value), None).to_dict(orient="records"))
        if isinstance(value, pd.Series):
            return make_json_safe(value.where(pd.notna(value), None).tolist())
    if hasattr(value, "item"):
        try:
            return make_json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


@router.post("/upload_file")
async def upload_file_api(
    request: Request,
    chatid: Optional[str] = Form(None),
    file: List[UploadFile] = File(...),
    sub_name_rows: Optional[str] = Form(None),
    table_header_rows: Optional[str] = Form(None),
):
    if not chatid:
        chatid = f"excel_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    user = get_current_user(request)
    user_id = user.get("id") if user else None
    session_service.create_or_update_session(chatid, "0", "__excel__", user_id, context_type="excel", context_ref_name="__excel__")

    form_data = await request.form()
    sub_name_rows_list = form_data.getlist("sub_name_rows")
    table_header_rows_list = form_data.getlist("table_header_rows")

    saved_paths: list[str] = []
    metadata: list[dict[str, Any]] = []
    file_configs: dict[str, Any] = {}
    chat_path = get_chat_path(chatid)

    for i, f in enumerate(file):
        raw_name = f.filename or f"upload_{uuid.uuid4().hex}.xlsx"
        upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{raw_name}"
        content = await f.read()
        upload_path.write_bytes(content)

        dst_path = chat_path / raw_name
        shutil.copy2(upload_path, dst_path)

        sub_name_value = sub_name_rows_list[i] if i < len(sub_name_rows_list) else sub_name_rows
        header_value = table_header_rows_list[i] if i < len(table_header_rows_list) else table_header_rows
        sub_name_range = parse_range_param(sub_name_value)
        header_range = parse_range_param(header_value)

        split_files = preprocess_file(str(dst_path), str(chat_path), chatid, raw_name, sub_name_range, header_range)
        saved_paths.extend(split_files)
        metadata.append({"file_name": raw_name, "saved_files": split_files})
        file_configs[raw_name] = {
            "table_header_rows": header_value or "",
            "sub_name_rows": sub_name_value or "",
        }

    db_utils.save_general_metadata(
        f"excel_upload_{chatid}",
        chatid,
        {
            "excel_paths": saved_paths,
            "sub_name_rows": sub_name_rows,
            "table_header_rows": table_header_rows,
            "file_configs": file_configs,
            "title": "Excel 分析",
            "timestamp": int(time.time() * 1000),
        },
    )
    progress_service.append_event(chatid, "upload", {"files": metadata})
    return JSONResponse(content={"status": "success", "chatid": chatid, "metadata": metadata})


@router.post("/ask")
async def ask_api(request: Request, payload: dict[str, Any]):
    chatid = payload.get("chatid")
    question = payload.get("question")
    if not chatid or not question:
        return JSONResponse(content={"status": "error", "message": "Missing chatid or question"}, status_code=400)

    session = session_service.get_session(chatid)
    if not session:
        return JSONResponse(content={"status": "error", "message": "Excel session not found"}, status_code=404)

    excel_paths = list_excel_paths(chatid)
    if not excel_paths:
        metadata = db_utils.get_general_metadata(f"excel_upload_{chatid}")
        general_content = metadata.get("general_content") if metadata else {}
        excel_paths = general_content.get("excel_paths", []) if isinstance(general_content, dict) else []
    if not excel_paths:
        return JSONResponse(content={"status": "error", "message": "Excel files not found"}, status_code=404)

    if session_service.is_general_context(session):
        return JSONResponse(content={"status": "error", "message": "当前会话未绑定 Excel 上下文"}, status_code=400)
    datasource_name = payload.get("datasource_name") or session_service.get_datasource_name(session) or "__excel__"
    user = get_current_user(request)
    user_id = user.get("id") if user else session.get("user_id")
    question_with_memory = memory_service.apply_to_question(question, user_id=user_id, chat_id=chatid, mode="excel")
    enable_analysis = bool(payload.get("enable_analysis"))
    skill_ids = payload.get("skill_ids")  # 用户选择的技能 ID 列表
    # 立即发送初始阶段事件
    progress_service.append_event(chatid, "stage", {
        "stage": "starting",
        "status": "running",
        "message": "正在启动 Excel 分析引擎…",
    })

    result = await asyncio.to_thread(
        askexcel_workflow_impl.run,
        {
            "question": question_with_memory,
            "excel_paths": excel_paths,
            "datasource_name": datasource_name,
            "chatid": chatid,
            "progress_callback": lambda event, data: progress_service.append_event(chatid, event, data),
            "enable_analysis": enable_analysis,
            "skill_ids": skill_ids,
        },
    )
    progress_service.done(chatid)

    structured = make_json_safe({
        "summary": result.get("summary") or result.get("report", ""),
        "code": result.get("code", ""),
        "result": result.get("result"),
        "chart": result.get("chart"),
        "trace": result.get("trace"),
        "thoughts": result.get("thoughts", []),
        "enable_analysis": enable_analysis,
        "request_options": {
            "datasource_name": datasource_name,
            "excel_paths": excel_paths,
            "skill_ids": skill_ids,
            "memory_count": payload.get("memory_count"),
        },
    })
    session_service.save_message(chatid, "user", question, user_id=user_id)
    session_service.save_message(chatid, "assistant", result.get("summary") or result.get("report", ""), structured, user_id=user_id)
    memory_service.schedule_extract_after_turn({
        "user_id": user_id,
        "chat_id": chatid,
        "mode": "excel",
        "question": question,
        "answer": result.get("summary") or result.get("report", ""),
        "structured": structured,
        "context": session_service.get_context_payload(session),
    })
    session_service.save_request_record(
        chat_id=chatid,
        knowledge_id=session.get("knowledge_id", "0"),
        user_question=question,
        retrieved_knowledge={"excel_paths": excel_paths},
        generated_sql=result.get("code", ""),
        execution_result=structured,
        user_id=user_id,
    )
    return JSONResponse(content=make_json_safe({
        "status": "success",
        "chatid": chatid,
        "summary": result.get("summary") or result.get("report", ""),
        "code": result.get("code", ""),
        "result": result.get("result"),
        "chart": result.get("chart"),
        "trace": result.get("trace"),
        "thoughts": result.get("thoughts", []),
    }))


@router.get("/progress")
async def get_progress_api(chatid: str = Query(...)):
    return JSONResponse(content=progress_service.get_excel(chatid))


@router.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


@router.get("/list_sessions")
async def list_sessions_api(request: Request):
    user = get_current_user(request)
    user_id = user.get("id") if user else None
    is_admin = is_admin_or_manager(user)
    sessions = []
    for s in session_service.list_sessions(user_id, is_admin):
        if not str(s.get("chat_id", "")).startswith("excel_"):
            continue
        metadata = db_utils.get_general_metadata(f"excel_upload_{s['chat_id']}") or {}
        general_content = metadata.get("general_content") if isinstance(metadata, dict) else {}
        files = list_excel_paths(s["chat_id"])
        fallback_title = general_content.get("title", "Excel 分析") if isinstance(general_content, dict) else "Excel 分析"
        title = db_utils.get_session_title(s["chat_id"], fallback_title, user_id=None if is_admin else user_id)
        sessions.append(
            {
                "id": s["chat_id"],
                "file_count": len(files),
                "title": title,
                "datasource_name": general_content.get("display_datasource_name") if isinstance(general_content, dict) else s.get("datasource_name"),
                "real_datasource_name": general_content.get("real_datasource_name") if isinstance(general_content, dict) else s.get("datasource_name"),
                "context": session_service.get_context_payload(s),
                "timestamp": general_content.get("timestamp", int(time.time() * 1000)) if isinstance(general_content, dict) else int(time.time() * 1000),
                "owner_username": user.get("username", "local-user") if user else "local-user",
            }
        )
    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return JSONResponse(content={"status": "success", "sessions": sessions})


@router.get("/sessions/{chat_id}/messages")
async def get_excel_session_messages(chat_id: str, request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        is_admin = is_admin_or_manager(user)
        session_data = session_service.get_session(chat_id)
        if not session_data:
            return JSONResponse(content={"success": False, "error": "会话不存在"}, status_code=404)
        owner_id = session_data.get("user_id")
        if owner_id != user_id and not is_admin:
            return JSONResponse(content={"success": False, "error": "无权查看该会话"}, status_code=403)
        messages = session_service.get_messages(chat_id, user_id=user_id if not is_admin else None)
        formatted = [{"role": msg["role"], "content": msg["content"], "structuredData": msg.get("structured_data"), "create_time": msg.get("create_time")} for msg in messages]
        return JSONResponse(content={"success": True, "messages": formatted})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/get_file_data")
async def get_file_data_api(chatid: str = Query(...)):
    session = session_service.get_session(chatid)
    if not session:
        return JSONResponse(content={"status": "error", "message": "Excel session not found"}, status_code=404)
    files = list_excel_paths(chatid)
    if not files:
        metadata = db_utils.get_general_metadata(f"excel_upload_{chatid}")
        general_content = metadata.get("general_content") if metadata else {}
        files = general_content.get("excel_paths", []) if isinstance(general_content, dict) else []

    data = []
    for path in files:
        path_obj = Path(path)
        if not path_obj.exists():
            continue
        name = path_obj.name
        kind = "[已处理]" if "__" in name or name.startswith("processed__") or "modified" in name else "[原始]"
        display_name = name
        display_sheet_name = "Sheet1"
        if "__" in name:
            parts = name.rsplit("__", 1)
            ext = path_obj.suffix
            display_name = parts[0] + ext
            display_sheet_name = parts[1].replace(ext, "")
        elif name.startswith("processed__"):
            display_name = name.replace("processed__", "")
        try:
            import pandas as pd

            if path_obj.suffix.lower() == ".csv":
                df_dict = {"Sheet1": pd.read_csv(path_obj)}
            else:
                df_dict = pd.read_excel(path_obj, sheet_name=None)

            is_original = kind == "[原始]"
            for sheet_name, df in df_dict.items():
                rows = make_json_safe(df.where(pd.notna(df), None).head(50).to_dict(orient="records"))
                columns = [str(col) for col in df.columns.tolist()]
                row_count = len(df)
                data.append({
                    "filename": f"{kind} {display_name}",
                    "real_filename": name,
                    "sheet_name": display_sheet_name if len(df_dict) == 1 else sheet_name,
                    "data": rows,
                    "columns": columns,
                    "row_count": row_count,
                    "is_original": is_original,
                })
        except Exception:
            data.append({"filename": f"{kind} {display_name}", "real_filename": name, "sheet_name": "Sheet1", "data": [], "columns": [], "row_count": 0, "is_original": kind == "[原始]"})
    return JSONResponse(content={"status": "success", "data": data, "files": files})


@router.delete("/delete_chat")
async def delete_chat_api(chatid: str = Query(...)):
    db_utils.execute_query(f"DELETE FROM {TABLE_MESSAGES} WHERE chat_id = %s", (chatid,))
    db_utils.execute_query(f"DELETE FROM {TABLE_REQUEST_RECORD} WHERE chat_id = %s", (chatid,))
    memory_service.clear_session_memory(chatid)
    db_utils.execute_query(f"DELETE FROM {db_utils.db_config.get('database_schema', 'public')}.askbi_chat_session WHERE chat_id = %s", (chatid,))
    progress_service.clear(chatid)
    chat_path = CHAT_DIR / chatid
    if chat_path.exists():
        shutil.rmtree(chat_path, ignore_errors=True)
    return JSONResponse(content={"status": "success", "chatid": chatid})


@router.get("/download_file")
async def download_file_api(chatid: str = Query(...), filename: Optional[str] = Query(None), is_modified: bool = Query(False)):
    session = session_service.get_session(chatid)
    if not session:
        return JSONResponse(content={"status": "error", "message": "Excel session not found"}, status_code=404)
    return JSONResponse(content={"status": "success", "chatid": chatid, "filename": filename, "is_modified": is_modified})


@router.post("/save_modified_file")
async def save_modified_file_api(payload: dict[str, Any]):
    return JSONResponse(content={"status": "success", "payload": payload})


@router.post("/save_original_file")
async def save_original_file_api(payload: dict[str, Any]):
    return JSONResponse(content={"status": "success", "payload": payload})


@router.post("/init_from_datasource")
async def init_from_datasource_api(request: Request):
    payload = {}
    try:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            payload = {k: v for k, v in form.items()}
        else:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
    except Exception:
        payload = {}
    chatid = payload.get("chatid") or f"excel_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    datasource_name = payload.get("datasource_name")
    datasource_display_name = datasource_name
    if datasource_name and ":" in datasource_name:
        datasource_display_name = datasource_name.split(":", 1)[1]
    user = get_current_user(request)
    user_id = user.get("id") if user else None
    if not datasource_name:
        return JSONResponse(content={"status": "error", "message": "缺少 datasource_name"}, status_code=400)
    from datasources.datasource_manager import datasource_manager
    ds = datasource_manager.get_datasource(datasource_name)
    if not ds or ds.get("type") != "excel":
        return JSONResponse(content={"status": "error", "message": "无效的 Excel 数据源"}, status_code=400)
    config = ds.get("config", {})
    file_dir = config.get("file_dir")
    files = config.get("files", [])
    file_configs = config.get("file_configs", {})
    skip_preprocess = config.get("skip_preprocess", False)
    if not file_dir or not Path(file_dir).exists() or not files:
        return JSONResponse(content={"status": "error", "message": "数据源中未找到有效文件"}, status_code=400)
    session_service.create_or_update_session(chatid, ds.get("knowledge_id", "0"), datasource_name, user_id, context_type="excel", context_ref_name=datasource_display_name)
    chat_path = get_chat_path(chatid)
    saved_paths = []
    metadata = []
    for filename in files:
        src = Path(file_dir) / filename
        if not src.exists():
            continue
        dst = chat_path / filename
        shutil.copy2(src, dst)
        if skip_preprocess:
            saved_paths.append(str(dst))
            meta = get_file_metadata(str(dst))
            if meta:
                metadata.append(meta)
            continue
        file_config = file_configs.get(filename, {}) if isinstance(file_configs, dict) else {}
        header_range = parse_range_param(file_config.get("table_header_rows"))
        sub_name_range = parse_range_param(file_config.get("sub_name_rows"))
        split_files = preprocess_file(str(dst), str(chat_path), chatid, filename, sub_name_range, header_range)
        saved_paths.extend(split_files)
        metadata.append({"file_name": filename, "saved_files": split_files})
        metadata.append({"file_name": filename, "saved_files": [str(dst)]})
    db_utils.save_general_metadata(
        f"excel_upload_{chatid}",
        chatid,
        {"excel_paths": saved_paths, "title": f"{datasource_display_name} 分析" if datasource_display_name else "Excel 分析", "timestamp": int(time.time() * 1000), "datasource_name": datasource_name, "real_datasource_name": datasource_name, "display_datasource_name": datasource_display_name, "file_configs": file_configs},
    )
    return JSONResponse(content={"status": "success", "chatid": chatid, "metadata": metadata})


# ==================== SSE 流式推送 ====================

@router.get("/stream")
async def stream_excel(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    """SSE 流式推送 Excel 分析进度。"""
    from utils.auth_utils import TOKEN_CACHE
    user = TOKEN_CACHE.get(token) if token else None
    if not user:
        user = get_current_user(request)
    if not user:
        return JSONResponse(content={"error": "未登录"}, status_code=401)

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    progress_service.register_queue(chatid, queue, loop)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if event.get("type") == "done":
                    break
        finally:
            progress_service.unregister_queue(chatid)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
