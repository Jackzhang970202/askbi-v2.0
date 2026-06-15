"""团队管理 API 路由。"""
from __future__ import annotations

import asyncio
import json
import traceback
import uuid

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.ask.agents_config.agent_manager import agent_manager
from backend.ask.services.progress_service import progress_service
from backend.ask.services.session_service import session_service
from backend.ask.services.memory_service import memory_service
from utils.auth_utils import get_current_user, is_admin_or_manager, TOKEN_CACHE
from utils.db_utils import db_utils

router = APIRouter()


# ── 团队 CRUD ──

@router.get("")
async def list_teams():
    teams = db_utils.list_teams()
    return JSONResponse(content={"success": True, "teams": teams})


@router.get("/{team_id}")
async def get_team(team_id: int):
    team = db_utils.get_team(team_id)
    if not team:
        return JSONResponse(content={"success": False, "error": "团队不存在"}, status_code=404)
    members = db_utils.list_team_members(team_id)
    team["members"] = members
    return JSONResponse(content={"success": True, "team": team})


@router.post("")
async def create_team(request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    required = ("name", "leader_config")
    for field in required:
        if not body.get(field):
            return JSONResponse(
                content={"success": False, "error": f"{field} 为必填项"},
                status_code=400,
            )
    user_id = user.get("id") if user else None
    members = body.pop("members", [])
    team_id = db_utils.create_team(body, user_id)
    if team_id is None:
        return JSONResponse(content={"success": False, "error": "创建失败"}, status_code=400)

    # 创建成员
    for m in members:
        m["team_id"] = team_id
        db_utils.create_team_member(m)

    return JSONResponse(content={"success": True, "team": {"id": team_id, "name": body["name"]}})


@router.put("/{team_id}")
async def update_team(team_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()

    # 更新团队基本信息
    members = body.pop("members", None)
    ok = db_utils.update_team(team_id, body)
    if not ok:
        return JSONResponse(content={"success": False, "error": "更新失败"}, status_code=400)

    # 如果传了 members，全量替换
    if members is not None:
        db_utils.delete_team_members(team_id)
        for m in members:
            m["team_id"] = team_id
            db_utils.create_team_member(m)

    return JSONResponse(content={"success": True})


@router.delete("/{team_id}")
async def delete_team(team_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)

    # 检查是否被其他团队引用为子团队
    referencing = db_utils.find_teams_referencing_sub_team(team_id)
    if referencing:
        names = ", ".join(referencing)
        return JSONResponse(
            content={"success": False, "error": f"该团队被以下团队的子团队引用: {names}"},
            status_code=400,
        )

    ok = db_utils.delete_team(team_id)
    if ok:
        db_utils.delete_team_members(team_id)
    return JSONResponse(content={"success": ok, "error": None if ok else "删除失败"})


@router.post("/{team_id}/test")
async def test_team(team_id: int, request: Request):
    """测试运行团队（单次对话）。"""
    body = await request.json()
    message = body.get("message", "")
    datasource_name = body.get("datasource_name")
    skill_ids = body.get("skill_ids")
    if not message:
        return JSONResponse(content={"success": False, "error": "message 为必填项"}, status_code=400)

    try:
        from backend.ask.team_engine.team_loader import load_team
        from backend.ask.team_engine.coordinator import TeamCoordinator
        import uuid

        team_config = load_team(team_id)
        if not team_config:
            return JSONResponse(content={"success": False, "error": "团队不存在"}, status_code=404)

        chatid = f"test_team_{uuid.uuid4().hex[:8]}"
        coordinator = TeamCoordinator(
            team_config=team_config,
            chatid=chatid,
            datasource_name=datasource_name,
            skill_ids=skill_ids,
        )
        result = coordinator.run(message)
        return JSONResponse(content={"success": True, "result": result})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# ── 自定义智能体创建（含 .py 文件生成）──

@router.post("/agents/custom")
async def create_custom_agent(request: Request):
    """创建自定义智能体: DB 记录 + 自动生成 .py 文件。"""
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    required = ("name", "display_name", "base_instructions")
    for field in required:
        if not body.get(field):
            return JSONResponse(
                content={"success": False, "error": f"{field} 为必填项"},
                status_code=400,
            )
    user_id = user.get("id") if user else None
    result = agent_manager.create_custom_agent(body, user_id)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


# ── 团队运行 + SSE 流式推送 ──

@router.post("/{team_id}/run")
async def run_team(team_id: int, request: Request):
    """与团队对话: 走 TeamCoordinator，推送 SSE 进度。"""
    try:
        body = await request.json()
        chatid = body.get("chatid")
        question = body.get("question")
        datasource_name = body.get("datasource_name")
        skill_ids = body.get("skill_ids")
        if not chatid or not question:
            return JSONResponse(content={"error": "Missing chatid or question"}, status_code=400)

        user = get_current_user(request)
        user_id = user.get("id") if user else None

        from backend.ask.team_engine.team_loader import load_team
        from backend.ask.team_engine.coordinator import TeamCoordinator

        team_config = load_team(team_id)
        if not team_config:
            return JSONResponse(content={"error": "团队不存在"}, status_code=404)

        progress_service.init(chatid)
        session = session_service.get_session(chatid)
        if not session:
            session_service.create_or_update_session(
                chatid,
                "0",
                datasource_name,
                user_id,
                context_type="team",
                context_ref_id=str(team_id),
                context_ref_name=team_config.get("name", ""),
            )
        else:
            session_service.update_context(chatid, "team", str(team_id), team_config.get("name", ""), datasource_name)

        def progress_callback(text: str):
            try:
                data = json.loads(text)
                progress_service.append_event(chatid, data.get("stage", "team_event"), data)
            except (json.JSONDecodeError, TypeError):
                progress_service.append_text(chatid, text)

        coordinator = TeamCoordinator(
            team_config=team_config,
            chatid=chatid,
            datasource_name=datasource_name,
            skill_ids=skill_ids,
            progress_callback=progress_callback,
        )

        question_with_memory = memory_service.apply_to_question(question, user_id=user_id, chat_id=chatid, mode="team")
        result = await asyncio.to_thread(coordinator.run, question_with_memory)
        progress_service.done(chatid)

        # 保存消息
        session_service.save_message(chatid, "user", question, user_id=user_id)
        answer = result.get("answer", str(result))
        structured = {
            "summary": answer,
            "team_id": team_id,
            "team_name": team_config.get("name", ""),
            "interactions": result.get("interactions", []),
            "request_options": {
                "datasource_name": datasource_name,
                "skill_ids": skill_ids,
            },
        }
        session_service.save_message(chatid, "assistant", answer, structured, user_id=user_id)
        memory_service.schedule_extract_after_turn({
            "user_id": user_id,
            "chat_id": chatid,
            "mode": "team",
            "question": question,
            "answer": answer,
            "structured": structured,
            "context": session_service.get_context_payload(session),
        })

        return JSONResponse(content={
            "status": "success",
            "chatid": chatid,
            "answer": answer,
            "summary": answer,
            "team_name": team_config.get("name", ""),
        })
    except Exception as e:
        traceback.print_exc()
        chatid = body.get("chatid") if "body" in locals() else ""
        if chatid:
            progress_service.done(chatid)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.get("/{team_id}/stream")
async def stream_team(
    team_id: int,
    chatid: str = Query(...),
    token: str = Query(""),
    request: Request = None,
):
    """SSE 流式推送团队决策过程。"""
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
