"""技能管理 API 路由。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.ask.skills.skill_manager import skill_manager
from utils.auth_utils import get_current_user, is_admin_or_manager

router = APIRouter()


@router.get("")
async def list_skills(category: str = None, active_only: bool = False):
    skills = skill_manager.list_skills(category=category, active_only=active_only)
    return JSONResponse(content={"success": True, "skills": skills})


@router.get("/{skill_id}")
async def get_skill(skill_id: int):
    skill = skill_manager.get_skill(skill_id)
    if not skill:
        return JSONResponse(content={"success": False, "error": "技能不存在"}, status_code=404)
    return JSONResponse(content={"success": True, "skill": skill})


@router.post("")
async def create_skill(request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    if not body.get("name") or not body.get("instructions"):
        return JSONResponse(content={"success": False, "error": "name 和 instructions 为必填项"}, status_code=400)
    user_id = user.get("id") if user else None
    result = skill_manager.create_skill(body, user_id)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.put("/{skill_id}")
async def update_skill(skill_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    result = skill_manager.update_skill(skill_id, body)
    status = 200 if result["success"] else 400
    return JSONResponse(content=result, status_code=status)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    result = skill_manager.delete_skill(skill_id)
    status = 200 if result["success"] else 403
    return JSONResponse(content=result, status_code=status)


@router.patch("/{skill_id}/toggle")
async def toggle_skill(skill_id: int, request: Request):
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    is_active = body.get("is_active", True)
    result = skill_manager.toggle_skill(skill_id, is_active)
    return JSONResponse(content=result)


@router.post("/{skill_id}/test")
async def test_skill(skill_id: int, request: Request):
    """测试技能：返回拼接后的完整 system prompt。"""
    skill = skill_manager.get_skill(skill_id)
    if not skill:
        return JSONResponse(content={"success": False, "error": "技能不存在"}, status_code=404)
    body = await request.json()
    agent_name = body.get("agent_name", "bi_sql_agent")

    from backend.ask.skills.skill_registry import SkillRegistry
    prompt_block = SkillRegistry.build_skill_prompt_block([skill])
    full_prompt = f"{skill.get('instructions', '')}\n{prompt_block}"
    return JSONResponse(content={
        "success": True,
        "full_system_prompt": full_prompt,
        "skill_instructions": prompt_block,
    })


@router.post("/ai-generate")
async def ai_generate_skill(request: Request):
    """AI 辅助创建：根据描述生成技能指令。"""
    user = get_current_user(request)
    if not is_admin_or_manager(user):
        return JSONResponse(content={"success": False, "error": "无权限"}, status_code=403)
    body = await request.json()
    description = body.get("description", "")
    category = body.get("category", "general")
    if not description:
        return JSONResponse(content={"success": False, "error": "description 为必填项"}, status_code=400)

    try:
        from core import get_model
        model = get_model()
        system_prompt = (
            "你是技能指令生成专家。根据用户的描述，生成一段 Markdown 格式的技能指令。\n"
            "要求：\n"
            "1. 输出纯 Markdown 文本\n"
            "2. 包含明确的规则条目\n"
            "3. 语言简洁、可执行\n"
            "4. 不要输出额外解释"
        )
        response = model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分类: {category}\n描述: {description}\n\n请生成技能指令。"},
        ])
        instructions = response.content if hasattr(response, "content") else str(response)
        return JSONResponse(content={"success": True, "instructions": instructions})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)
