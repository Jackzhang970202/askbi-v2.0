from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from backend.ask.services.memory_service import memory_service
from utils.auth_utils import get_current_user

router = APIRouter()


def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise PermissionError("未登录或登录已过期")
    return user


@router.get("/user")
async def list_user_memories(
    request: Request,
    status: str = Query("active"),
    memory_kind: str | None = Query(None),
    keyword: str | None = Query(None),
    user_id: int | None = Query(None),
):
    try:
        user = _require_user(request)
        memories = memory_service.list_user_memories(user, status=status, memory_kind=memory_kind, keyword=keyword, target_user_id=user_id)
        return JSONResponse(content={"success": True, "memories": memories})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.get("/session/{chat_id}")
async def list_session_memories(chat_id: str, request: Request, status: str = Query("active")):
    try:
        user = _require_user(request)
        target_chat_id = None if chat_id == '_all' else chat_id
        memories = memory_service.list_session_memories(target_chat_id, user, status=status)
        return JSONResponse(content={"success": True, "memories": memories})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.put("/{scope}/{memory_id}")
async def update_memory(scope: str, memory_id: int, request: Request):
    try:
        if scope not in ("user", "session"):
            return JSONResponse(content={"success": False, "error": "scope 必须是 user 或 session"}, status_code=400)
        user = _require_user(request)
        data = await request.json()
        payload = data if isinstance(data, dict) else {}
        if scope == "session" and not payload.get("chat_id"):
            return JSONResponse(content={"success": False, "error": "session 记忆更新必须传 chat_id"}, status_code=400)
        memory_service.update_memory(scope, memory_id, user, payload)
        return JSONResponse(content={"success": True})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.patch("/{scope}/{memory_id}/archive")
async def archive_memory(scope: str, memory_id: int, request: Request):
    try:
        if scope not in ("user", "session"):
            return JSONResponse(content={"success": False, "error": "scope 必须是 user 或 session"}, status_code=400)
        user = _require_user(request)
        memory_service.archive_memory(scope, memory_id, user)
        return JSONResponse(content={"success": True})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.delete("/{scope}/{memory_id}")
async def delete_memory(scope: str, memory_id: int, request: Request):
    try:
        if scope not in ("user", "session"):
            return JSONResponse(content={"success": False, "error": "scope 必须是 user 或 session"}, status_code=400)
        user = _require_user(request)
        memory_service.delete_memory(scope, memory_id, user)
        return JSONResponse(content={"success": True})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.post("/session/{chat_id}/summarize")
async def summarize_session(chat_id: str, request: Request):
    try:
        user = _require_user(request)
        memory_service.schedule_extract_after_turn({
            "user_id": user.get("id"),
            "chat_id": chat_id,
            "question": "手动总结当前会话",
            "context": {"manual_summarize": True},
        })
        return JSONResponse(content={"success": True})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)


@router.get("/events")
async def list_events(request: Request, chatid: str | None = Query(None), limit: int = Query(100)):
    try:
        user = _require_user(request)
        events = memory_service.list_events(user, chat_id=chatid, limit=limit)
        return JSONResponse(content={"success": True, "events": events})
    except PermissionError as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=401)
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=500)
