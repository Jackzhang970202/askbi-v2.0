from __future__ import annotations

import asyncio
import json
import time
import traceback
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.ask.services.progress_service import progress_service
from backend.ask.services.session_service import session_service
from backend.ask.services.memory_service import memory_service
from backend.ask.workflows.bi_workflow import bi_workflow
from backend.ask.agents_config.agent_manager import agent_manager
from utils.auth_utils import get_current_user, is_admin_or_manager
from utils.db_utils import db_utils
from config.config_db import TABLE_MESSAGES, TABLE_REQUEST_RECORD
from openai import OpenAI

router = APIRouter()


@router.post("/upload_file")
async def upload_file_placeholder():
    return JSONResponse(content={"success": False, "error": "BI 模式不支持 upload_file，请使用 /excel/upload_file"}, status_code=400)


@router.get("/progress")
async def get_progress(chatid: str = Query(...), offset: int = Query(0)):
    return JSONResponse(content=progress_service.get_bi(chatid, offset))


@router.post("/create_chat")
async def create_chat(request: Request):
    try:
        db_utils.bootstrap_chat_session_context_columns()
        body = await request.json()
        knowledge_id = body.get("knowledge_id", "0")
        datasource_name = body.get("datasource_name")
        context_type = body.get("context_type") or ("bi" if datasource_name else "general")
        chat_id = body.get("chat_id") or f"chat_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        context_ref_name = datasource_name if context_type in ("bi", "excel") else body.get("context_ref_name")
        context_ref_id = str(body.get("context_ref_id")) if body.get("context_ref_id") is not None else None
        if context_type == "general":
            datasource_name = None
        if not session_service.create_or_update_session(
            chat_id,
            knowledge_id,
            datasource_name,
            user_id,
            context_type=context_type,
            context_ref_id=context_ref_id,
            context_ref_name=context_ref_name,
        ):
            return JSONResponse(content={"status": "error", "message": "创建会话失败"}, status_code=500)
        return JSONResponse(content={
            "status": "success",
            "chat_id": chat_id,
            "knowledge_id": knowledge_id,
            "context": {
                "type": context_type,
                "ref_id": context_ref_id,
                "ref_name": context_ref_name,
                "datasource_name": datasource_name,
            },
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.post("/chat/context")
async def update_chat_context(request: Request):
    try:
        body = await request.json()
        chat_id = body.get("chatid")
        context_type = body.get("context_type") or "general"
        if not chat_id:
            return JSONResponse(content={"success": False, "error": "缺少 chatid"}, status_code=400)
        session = session_service.get_session(chat_id)
        if not session:
            return JSONResponse(content={"success": False, "error": "会话不存在"}, status_code=404)
        context_ref_id = str(body.get("context_ref_id")) if body.get("context_ref_id") is not None else None
        context_ref_name = body.get("context_ref_name")
        datasource_name = body.get("datasource_name")
        if context_type == "team" and not context_ref_id:
            return JSONResponse(content={"success": False, "error": "缺少 team id"}, status_code=400)
        if context_type in ("bi", "excel") and not datasource_name:
            return JSONResponse(content={"success": False, "error": "缺少 datasource_name"}, status_code=400)
        ok = session_service.update_context(chat_id, context_type, context_ref_id, context_ref_name, datasource_name)
        if not ok:
            return JSONResponse(content={"success": False, "error": "更新上下文失败"}, status_code=500)
        updated = session_service.get_session(chat_id)
        return JSONResponse(content={"success": True, "chat_id": chat_id, "context": session_service.get_context_payload(updated)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/chat/context/clear")
async def clear_chat_context(request: Request):
    try:
        body = await request.json()
        chat_id = body.get("chatid")
        if not chat_id:
            return JSONResponse(content={"success": False, "error": "缺少 chatid"}, status_code=400)
        if not session_service.clear_context(chat_id):
            return JSONResponse(content={"success": False, "error": "清除上下文失败"}, status_code=500)
        updated = session_service.get_session(chat_id)
        return JSONResponse(content={"success": True, "chat_id": chat_id, "context": session_service.get_context_payload(updated)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/chat/ask")
async def ask_general(request: Request):
    try:
        body = await request.json()
        chatid = body.get("chatid")
        question = body.get("question")
        if not chatid or not question:
            return JSONResponse(content={"error": "Missing chatid or question"}, status_code=400)
        session = session_service.get_session(chatid)
        if not session:
            return JSONResponse(content={"error": "会话不存在"}, status_code=404)
        if not session_service.is_general_context(session):
            return JSONResponse(content={"error": "当前会话不是普通对话上下文"}, status_code=400)
        user = get_current_user(request)
        user_id = user.get("id") if user else session.get("user_id")
        conf_agent = agent_manager.get_agent_config("normal_chat_agent", skill_ids=body.get("skill_ids"))
        from config.config_db import _load_config as load_conf
        model_conf = conf_agent.get("model_config") or load_conf()
        client = OpenAI(
            api_key=model_conf.get("api_key", ""),
            base_url=model_conf.get("base_url", ""),
            timeout=90.0,
        )
        now = datetime.now()
        current_time_prompt = (
            f"当前系统时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"今天是：{now.strftime('%Y年%m月%d日')}\n"
            f"星期：{'一二三四五六日'[now.weekday()]}"
        )
        system_prompt = current_time_prompt + "\n\n" + conf_agent.get("instructions", "") + (("\n" + conf_agent.get("skill_prompt", "")) if conf_agent.get("skill_prompt") else "")
        messages = [{"role": "system", "content": system_prompt}]
        history = session_service.get_messages(chatid, user_id=user_id)
        for msg in history[-10:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        question_with_memory = memory_service.apply_to_question(question, user_id=user_id, chat_id=chatid, mode="general")
        messages.append({"role": "user", "content": question_with_memory})
        result = client.chat.completions.create(
            model=model_conf.get("model", ""),
            messages=messages,
            temperature=model_conf.get("temperature", 0.1),
            extra_body={"enable_thinking": False},
        )
        answer = (result.choices[0].message.content or "").strip()
        session_service.save_message(chatid, "user", question, user_id=user_id)
        structured = {
            "summary": answer,
            "request_options": {
                "skill_ids": body.get("skill_ids"),
                "memory_context_count": 10,
            },
        }
        session_service.save_message(chatid, "assistant", answer, structured, user_id=user_id)
        memory_service.schedule_extract_after_turn({
            "user_id": user_id,
            "chat_id": chatid,
            "mode": "general",
            "question": question,
            "answer": answer,
            "structured": structured,
            "context": session_service.get_context_payload(session),
        })
        return JSONResponse(content={"status": "success", "chatid": chatid, "answer": answer, "summary": answer})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.get("/chat/sessions/{chat_id}")
async def get_chat_session_detail(chat_id: str, request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        session = session_service.get_session(chat_id)
        if not session:
            return JSONResponse(content={"success": False, "error": "会话不存在"}, status_code=404)
        if session.get("user_id") != user_id and not can_view_all:
            return JSONResponse(content={"success": False, "error": "无权查看该会话"}, status_code=403)
        return JSONResponse(content={"success": True, "session": session, "context": session_service.get_context_payload(session)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/chat/sessions")
async def list_all_chat_sessions(request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        sessions = []
        for s in session_service.list_sessions(user_id, can_view_all):
            context = session_service.get_context_payload(s)
            sessions.append({
                "id": s.get("chat_id"),
                "knowledge_id": s.get("knowledge_id", "0"),
                "datasource_name": s.get("datasource_name"),
                "context": context,
                "create_time": s.get("create_time"),
                "timestamp": int(time.time() * 1000),
                "user_id": s.get("user_id"),
                "owner_username": user.get("username") if user else None,
            })
        return JSONResponse(content={"success": True, "sessions": sessions})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/chat/stream")
async def stream_general(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    return await stream_bi(chatid=chatid, token=token, request=request)


@router.get("/chat/context")
async def get_chat_context(chatid: str = Query(...), request: Request = None):
    try:
        session = session_service.get_session(chatid)
        if not session:
            return JSONResponse(content={"success": False, "error": "会话不存在"}, status_code=404)
        return JSONResponse(content={"success": True, "context": session_service.get_context_payload(session)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/chat/messages/{chat_id}")
async def get_chat_messages(chat_id: str, request: Request):
    return await get_bi_session_messages(chat_id, request)


@router.delete("/chat/sessions/{chat_id}")
async def delete_chat_session(chat_id: str, request: Request):
    return await delete_bi_session(chat_id, request)


@router.post("/chat/create")
async def create_general_chat(request: Request):
    return await create_chat(request)


@router.post("/chat/create-general")
async def create_general_chat_alias(request: Request):
    return await create_chat(request)


@router.post("/chat/create-bi")
async def create_bi_chat_alias(request: Request):
    return await create_chat(request)


@router.post("/chat/create-excel")
async def create_excel_chat_alias(request: Request):
    return await create_chat(request)


@router.post("/chat/create-team")
async def create_team_chat_alias(request: Request):
    return await create_chat(request)


@router.post("/chat/update-context")
async def update_chat_context_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/clear-context")
async def clear_chat_context_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/ask-general")
async def ask_general_alias(request: Request):
    return await ask_general(request)


@router.get("/chat/detail/{chat_id}")
async def get_chat_session_detail_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.get("/chat/list")
async def list_all_chat_sessions_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/progress")
async def get_general_progress(chatid: str = Query(...), offset: int = Query(0)):
    return await get_progress(chatid, offset)


@router.get("/chat/history/{chat_id}")
async def get_chat_messages_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/delete/{chat_id}")
async def delete_chat_session_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.get("/chat/context/detail")
async def get_chat_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.get("/chat/context/stream")
async def stream_general_alias(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.post("/chat/attach-context")
async def update_chat_context_attach_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/detach-context")
async def clear_chat_context_detach_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/current-context")
async def get_chat_current_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/context/select")
async def update_chat_context_select_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/context/remove")
async def clear_chat_context_remove_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/context/get")
async def get_chat_context_get_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/general/ask")
async def ask_general_explicit_alias(request: Request):
    return await ask_general(request)


@router.post("/chat/general/create")
async def create_general_explicit_alias(request: Request):
    return await create_chat(request)


@router.post("/chat/context/set")
async def update_chat_context_set_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/context/reset")
async def clear_chat_context_reset_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/session/{chat_id}")
async def get_chat_session_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.get("/chat/session-list")
async def get_chat_session_list_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/message-list/{chat_id}")
async def get_chat_message_list_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/session/{chat_id}")
async def delete_chat_session_path_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.get("/chat/event-stream")
async def stream_general_event_alias(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.get("/chat/context-state")
async def get_chat_context_state_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/context-state")
async def set_chat_context_state_alias(request: Request):
    return await update_chat_context(request)


@router.delete("/chat/context-state")
async def clear_chat_context_state_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/general/stream")
async def stream_general_explicit_alias(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.get("/chat/general/progress")
async def get_general_progress_alias(chatid: str = Query(...), offset: int = Query(0)):
    return await get_progress(chatid, offset)


@router.post("/chat/context/switch")
async def switch_chat_context_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/context/unset")
async def unset_chat_context_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/context/use")
async def use_chat_context_alias(request: Request):
    return await update_chat_context(request)


@router.post("/chat/context/drop")
async def drop_chat_context_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/message")
async def ask_chat_message_alias(request: Request):
    return await ask_general(request)


@router.post("/chat/context/general")
async def make_chat_general(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/context/info")
async def get_chat_context_info_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/context/info")
async def post_chat_context_info_alias(request: Request):
    return await update_chat_context(request)


@router.delete("/chat/context/info")
async def delete_chat_context_info_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/general")
async def ask_general_short_alias(request: Request):
    return await ask_general(request)


@router.get("/chat/general/messages/{chat_id}")
async def get_general_messages_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/general/sessions/{chat_id}")
async def delete_general_session_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.get("/chat/general/sessions")
async def list_general_sessions_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.post("/chat/general/context")
async def set_general_context_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/general/context")
async def get_general_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.get("/chat/general/detail/{chat_id}")
async def get_general_detail_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.post("/chat/general/create-empty")
async def create_general_empty_alias(request: Request):
    return await create_chat(request)


@router.get("/chat/general/event-stream")
async def get_general_event_stream_alias(chatid: str = Query(...), token: str = Query(""), request: Request = None):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.post("/chat/general/context/clear")
async def clear_general_context_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/general/context/set")
async def set_general_context_state_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/general/context-state")
async def get_general_context_state_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.get("/chat/general/list")
async def general_list_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/general/history/{chat_id}")
async def general_history_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/general/delete/{chat_id}")
async def general_delete_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.post("/chat/general/new")
async def general_new_alias(request: Request):
    return await create_chat(request)


@router.get("/chat/general/session/{chat_id}")
async def general_session_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.get("/chat/general/session-list")
async def general_session_list_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/general/progress-state")
async def general_progress_state_alias(chatid: str = Query(...), offset: int = Query(0)):
    return await get_progress(chatid, offset)


@router.post("/chat/context/general/restore")
async def restore_general_context_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/context/general/restore")
async def get_restore_general_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/context/team-or-ds")
async def set_context_team_or_ds_alias(request: Request):
    return await update_chat_context(request)


@router.get("/chat/context/team-or-ds")
async def get_context_team_or_ds_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.delete("/chat/context/team-or-ds")
async def clear_context_team_or_ds_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/query")
async def general_query_alias(request: Request):
    return await ask_general(request)


@router.get("/chat/query/context")
async def get_general_query_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/query/context")
async def post_general_query_context_alias(request: Request):
    return await update_chat_context(request)


@router.delete("/chat/query/context")
async def delete_general_query_context_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/query/stream")
async def general_query_stream_alias(chatid: str = Query(...), token: str = Query(""), request: Request = None):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.post("/chat/query/create")
async def general_query_create_alias(request: Request):
    return await create_chat(request)


@router.get("/chat/query/sessions")
async def general_query_sessions_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/query/messages/{chat_id}")
async def general_query_messages_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/query/sessions/{chat_id}")
async def general_query_delete_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.get("/chat/query/detail/{chat_id}")
async def general_query_detail_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.get("/chat/query/progress")
async def general_query_progress_alias(chatid: str = Query(...), offset: int = Query(0)):
    return await get_progress(chatid, offset)


@router.post("/chat/query/context/clear")
async def general_query_context_clear_alias(request: Request):
    return await clear_chat_context(request)


@router.post("/chat/query/context/set")
async def general_query_context_set_alias(request: Request):
    return await update_chat_context(request)


@router.get("/chat/query/context/get")
async def general_query_context_get_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/route")
async def general_route_alias(request: Request):
    return await ask_general(request)


@router.get("/chat/route/context")
async def general_route_context_alias(chatid: str = Query(...), request: Request = None):
    return await get_chat_context(chatid, request)


@router.post("/chat/route/context")
async def general_route_context_set_alias(request: Request):
    return await update_chat_context(request)


@router.delete("/chat/route/context")
async def general_route_context_clear_alias(request: Request):
    return await clear_chat_context(request)


@router.get("/chat/route/stream")
async def general_route_stream_alias(chatid: str = Query(...), token: str = Query(""), request: Request = None):
    return await stream_general(chatid=chatid, token=token, request=request)


@router.post("/chat/route/create")
async def general_route_create_alias(request: Request):
    return await create_chat(request)


@router.get("/chat/route/sessions")
async def general_route_sessions_alias(request: Request):
    return await list_all_chat_sessions(request)


@router.get("/chat/route/messages/{chat_id}")
async def general_route_messages_alias(chat_id: str, request: Request):
    return await get_chat_messages(chat_id, request)


@router.delete("/chat/route/sessions/{chat_id}")
async def general_route_delete_alias(chat_id: str, request: Request):
    return await delete_chat_session(chat_id, request)


@router.get("/chat/route/detail/{chat_id}")
async def general_route_detail_alias(chat_id: str, request: Request):
    return await get_chat_session_detail(chat_id, request)


@router.post("/ask")
async def ask_bi(request: Request):
    try:
        body = await request.json()
        chatid = body.get("chatid")
        question = body.get("question")
        knowledge_id = body.get("knowledge_id", "0")
        datasource_name = body.get("datasource_name")
        if not chatid or not question:
            return JSONResponse(content={"error": "Missing chatid or question"}, status_code=400)

        session = session_service.get_session(chatid)
        if session_service.is_general_context(session):
            return await ask_general(request)
        if session_service.is_team_context(session):
            return JSONResponse(content={"error": "当前会话为团队上下文，请使用团队链路"}, status_code=400)
        if not datasource_name:
            datasource_name = session_service.get_datasource_name(session)

        user = get_current_user(request)
        user_id = user.get("id") if user else None
        progress_service.init(chatid)

        # 立即发送初始阶段事件，让用户看到实时反馈
        progress_service.append_event(chatid, "stage", {
            "stage": "starting",
            "status": "running",
            "message": "正在启动问数引擎…",
        })

        enable_analysis = bool(body.get("enable_analysis"))
        skill_ids = body.get("skill_ids")  # 用户选择的技能 ID 列表，None 表示使用全部激活技能
        question_with_memory = memory_service.apply_to_question(question, user_id=user_id, chat_id=chatid, mode="bi")
        result = await asyncio.to_thread(
            bi_workflow.run,
            question_with_memory,
            datasource_name,
            progress_callback=lambda text: progress_service.append_text(chatid, text),
            enable_analysis=enable_analysis,
            chatid=chatid,
            active_skill_ids=skill_ids,
        )
        progress_service.done(chatid)

        session_service.save_message(chatid, "user", question, user_id=user_id)
        structured = {
            "summary": result.get("summary", ""),
            "sql": result.get("sql", ""),
            "tables": result.get("tables", []),
            "chart": result.get("chart"),
            "thoughts": result.get("thoughts", []),
            "result": result.get("result"),
            "enable_analysis": enable_analysis,
            "request_options": {
                "knowledge_id": knowledge_id,
                "datasource_name": datasource_name,
                "memory_count": body.get("memory_count"),
                "skill_ids": skill_ids,
            },
        }
        session_service.save_message(chatid, "assistant", result.get("summary", ""), structured, user_id=user_id)
        memory_service.schedule_extract_after_turn({
            "user_id": user_id,
            "chat_id": chatid,
            "mode": "bi",
            "question": question,
            "answer": result.get("summary", ""),
            "structured": structured,
            "context": session_service.get_context_payload(session),
        })
        session_service.save_request_record(
            chat_id=chatid,
            knowledge_id=knowledge_id,
            user_question=question,
            retrieved_knowledge={"datasource_name": datasource_name},
            generated_sql=result.get("sql", ""),
            execution_result=structured,
            user_id=user_id,
        )
        return JSONResponse(content={
            "status": "success",
            "chatid": chatid,
            "answer": result.get("summary", ""),
            "summary": result.get("summary", ""),
            "sql": result.get("sql", ""),
            "tables": result.get("tables", []),
            "chart": result.get("chart"),
            "thoughts": result.get("thoughts", []),
        })
    except Exception as e:
        traceback.print_exc()
        progress_service.done(body.get("chatid") if 'body' in locals() else "")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.get("/bi/sessions")
async def list_bi_sessions(request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        sessions = []
        for s in session_service.list_sessions(user_id, can_view_all):
            chat_id = str(s.get("chat_id", ""))
            if chat_id.startswith("excel_"):
                continue
            fallback_title = f"{s.get('datasource_name') or 'BI'} 分析"
            title = db_utils.get_session_title(chat_id, fallback_title, user_id=None if can_view_all else user_id)
            sessions.append(
                {
                    "id": chat_id,
                    "title": title,
                    "datasource_name": s.get("datasource_name"),
                    "real_datasource_name": s.get("datasource_name"),
                    "knowledge_id": s.get("knowledge_id", "0"),
                    "context": session_service.get_context_payload(s),
                    "create_time": s.get("create_time"),
                    "timestamp": int(time.time() * 1000),
                    "user_id": s.get("user_id"),
                    "owner_username": user.get("username") if user else None,
                }
            )
        return JSONResponse(content={"success": True, "sessions": sessions})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/bi/sessions/{chat_id}/messages")
async def get_bi_session_messages(chat_id: str, request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        session = session_service.get_session(chat_id)
        if not session:
            return JSONResponse(content={"success": False, "error": "会话不存在"}, status_code=404)
        if session.get("user_id") != user_id and not can_view_all:
            return JSONResponse(content={"success": False, "error": "无权查看该会话"}, status_code=403)
        messages = session_service.get_messages(chat_id, user_id=user_id if not can_view_all else None)
        return JSONResponse(content={"success": True, "messages": [{"role": msg["role"], "content": msg["content"], "structuredData": msg.get("structured_data"), "create_time": msg.get("create_time")} for msg in messages]})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/bi/sessions/{chat_id}")
async def delete_bi_session(chat_id: str, request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        session = session_service.get_session(chat_id)
        if session and session.get("user_id") != user_id and not can_view_all:
            return JSONResponse(content={"success": False, "error": "无权删除该会话"}, status_code=403)
        db_utils.execute_query(f"DELETE FROM {TABLE_MESSAGES} WHERE chat_id = %s", (chat_id,))
        db_utils.execute_query(f"DELETE FROM {TABLE_REQUEST_RECORD} WHERE chat_id = %s", (chat_id,))
        memory_service.clear_session_memory(chat_id, user_id=user_id)
        db_utils.execute_query(f"DELETE FROM {db_utils.db_config.get('database_schema', 'public')}.askbi_chat_session WHERE chat_id = %s", (chat_id,))
        progress_service.clear(chat_id)
        return JSONResponse(content={"success": True, "message": "会话已删除"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# ==================== SSE 流式推送 ====================

@router.get("/stream")
async def stream_bi(
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    """SSE 流式推送 BI 问数进度。前端通过 fetch + ReadableStream 消费。"""
    from utils.auth_utils import TOKEN_CACHE
    # SSE 场景下 token 通过 query param 传递
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
                    # 发送心跳保持连接
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
