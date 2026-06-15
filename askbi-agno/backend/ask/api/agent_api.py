"""智能体管理 API 路由。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.ask.agents_config.agent_manager import agent_manager
from utils.auth_utils import get_current_user, is_admin_or_manager

router = APIRouter()


@router.get("")
async def list_agents():
    agents = agent_manager.list_agents()
    return JSONResponse(content={"success": True, "agents": agents})


@router.get("/{agent_name}")
async def get_agent(agent_name: str):
    agent = agent_manager.get_agent_by_name(agent_name)
    if not agent:
        return JSONResponse(content={"success": False, "error": "智能体不存在"}, status_code=404)
    return JSONResponse(content={"success": True, "agent": agent})


@router.post("")
async def create_agent(request: Request):
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
    result = agent_manager.create_agent(body, user_id)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.put("/{agent_id}")
async def update_agent(agent_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    result = agent_manager.update_agent(agent_id, body)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    result = agent_manager.delete_agent(agent_id)
    status = 200 if result["success"] else 403
    return JSONResponse(content=result, status_code=status)


@router.post("/{agent_id}/bind-skills")
async def bind_skills(agent_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    skill_ids = body.get("skill_ids", [])
    if not isinstance(skill_ids, list):
        return JSONResponse(content={"success": False, "error": "skill_ids 必须为列表"}, status_code=400)
    result = agent_manager.bind_skills(agent_id, skill_ids)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.post("/{agent_id}/test")
async def test_agent(agent_id: int, request: Request):
    """对话测试：用临时 Agent 实例调用 LLM。"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        return JSONResponse(content={"success": False, "error": "智能体不存在"}, status_code=404)
    body = await request.json()
    message = body.get("message", "")
    if not message:
        return JSONResponse(content={"success": False, "error": "message 为必填项"}, status_code=400)

    try:
        from core import get_model
        model_config = agent_manager.get_merged_model_config(agent)
        from agno.models.openai import OpenAIChat
        model = OpenAIChat(
            id=model_config["model"] or "qwen-plus",
            api_key=model_config["api_key"] or "",
            base_url=model_config["base_url"] or "",
            temperature=model_config.get("temperature", 0.1),
        )
        instructions = agent.get("base_instructions", "")
        response = model.invoke([
            {"role": "system", "content": instructions},
            {"role": "user", "content": message},
        ])
        reply = response.content if hasattr(response, "content") else str(response)
        return JSONResponse(content={"success": True, "reply": reply})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/{agent_name}/reset")
async def reset_agent(agent_name: str, request: Request):
    """重置智能体为内置默认值。"""
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)

    from backend.ask.agents_config.agent_manager import BUILTIN_AGENTS
    builtin = None
    for b in BUILTIN_AGENTS:
        if b["name"] == agent_name:
            builtin = b
            break
    if not builtin:
        return JSONResponse(content={"success": False, "error": "未找到对应的内置智能体定义"}, status_code=404)

    agent = agent_manager.get_agent_by_name(agent_name)
    if not agent:
        return JSONResponse(content={"success": False, "error": "智能体不存在"}, status_code=404)

    result = agent_manager.update_agent(agent["id"], {
        "display_name": builtin["display_name"],
        "description": builtin["description"],
        "base_instructions": builtin["base_instructions"],
        "model_config": {},
        "bound_skills": [],
    })
    return JSONResponse(content=result)
