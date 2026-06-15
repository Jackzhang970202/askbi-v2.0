"""技能管理器：CRUD + 内置种子 + 缓存。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from utils.db_utils import db_utils

logger = logging.getLogger(__name__)

BUILTIN_SKILLS = [
    {
        "name": "sql_safety_rules",
        "description": "SQL 安全查询规则，强制仅使用 SELECT 语句",
        "category": "sql",
        "priority": 10,
        "instructions": (
            "## SQL 安全规则\n"
            "1. 只允许生成 SELECT / WITH ... SELECT 查询\n"
            "2. 禁止 INSERT / UPDATE / DELETE / ALTER / DROP / CREATE\n"
            "3. 不得编造不存在的表名或列名\n"
            "4. 涉及敏感字段时优先使用脱敏函数\n"
        ),
    },
    {
        "name": "report_format_rules",
        "description": "报告格式规范，确保输出清晰、结构化",
        "category": "report",
        "priority": 5,
        "instructions": (
            "## 报告格式规范\n"
            "1. 先直接回答用户问题\n"
            "2. 结论必须基于真实执行结果，不编造数据\n"
            "3. 列表结果先总结再提炼重点\n"
            "4. 不输出 SQL、代码或执行日志\n"
        ),
    },
    {
        "name": "chart_generation_rules",
        "description": "图表生成约束，确保图表合法有效",
        "category": "chart",
        "priority": 5,
        "instructions": (
            "## 图表生成约束\n"
            "1. 优先选择柱状图、折线图、饼图\n"
            "2. 背景设为透明\n"
            "3. 不编造数据字段\n"
            "4. 单个标量结果不生成图表\n"
            "5. 如果数据不适合可视化，明确说明\n"
        ),
    },
]


class SkillManager:
    """技能 CRUD 与种子管理。"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ts: float = 0
        self._cache_ttl = 60

    def _invalidate_cache(self):
        self._cache.clear()
        self._cache_ts = 0

    def _cache_expired(self) -> bool:
        return time.time() - self._cache_ts > self._cache_ttl

    def list_skills(self, category: Optional[str] = None, active_only: bool = False) -> List[Dict[str, Any]]:
        return db_utils.list_skills(category=category, active_only=active_only)

    def get_skill(self, skill_id: int) -> Optional[Dict[str, Any]]:
        return db_utils.get_skill(skill_id)

    def create_skill(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        if db_utils.get_skill_by_name(data["name"]):
            return {"success": False, "error": f"技能名称 '{data['name']}' 已存在"}
        skill_id = db_utils.create_skill(data, user_id)
        if skill_id is None:
            return {"success": False, "error": "创建失败"}
        self._invalidate_cache()
        return {"success": True, "skill": {"id": skill_id, "name": data["name"]}}

    def update_skill(self, skill_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        skill = db_utils.get_skill(skill_id)
        if not skill:
            return {"success": False, "error": "技能不存在"}
        if "name" in data and data["name"] != skill["name"]:
            existing = db_utils.get_skill_by_name(data["name"])
            if existing:
                return {"success": False, "error": f"技能名称 '{data['name']}' 已被使用"}
        ok = db_utils.update_skill(skill_id, data)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "更新失败"}

    def delete_skill(self, skill_id: int) -> Dict[str, Any]:
        skill = db_utils.get_skill(skill_id)
        if not skill:
            return {"success": False, "error": "技能不存在"}
        if skill.get("is_builtin"):
            return {"success": False, "error": "内置技能不可删除"}
        ok = db_utils.delete_skill(skill_id)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "删除失败"}

    def toggle_skill(self, skill_id: int, is_active: bool) -> Dict[str, Any]:
        ok = db_utils.toggle_skill(skill_id, is_active)
        if ok:
            self._invalidate_cache()
        return {"success": ok}

    def seed_builtin_skills(self):
        """幂等写入内置技能。"""
        for s in BUILTIN_SKILLS:
            if db_utils.get_skill_by_name(s["name"]):
                continue
            db_utils.create_skill(
                {**s, "is_builtin": True, "is_active": True},
                user_id=None,
            )
            logger.info("已创建内置技能: %s", s["name"])


skill_manager = SkillManager()
