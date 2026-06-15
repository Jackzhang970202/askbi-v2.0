"""技能注册表：运行时查找匹配技能并拼接 prompt 块。"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from utils.db_utils import db_utils


class SkillRegistry:
    """根据 agent_name + datasource_name 查找匹配的技能并拼接 instructions。"""

    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_ts: float = 0
        self._cache_ttl = 60

    def _load_active_skills(self) -> List[Dict[str, Any]]:
        cache_key = "__active__"
        if cache_key in self._cache and time.time() - self._cache_ts <= self._cache_ttl:
            return self._cache[cache_key]
        skills = db_utils.list_skills(active_only=True)
        self._cache[cache_key] = skills
        self._cache_ts = time.time()
        return skills

    def invalidate(self):
        self._cache.clear()
        self._cache_ts = 0

    def get_active_skill_instructions(
        self, agent_name: str, datasource_name: Optional[str] = None,
        skill_ids: Optional[List[int]] = None
    ) -> str:
        """返回拼接后的技能 prompt 块，如果没有匹配技能则返回空字符串。
        
        skill_ids: 用户指定的技能 ID 列表。为 None 时使用所有激活技能（原有行为）。
        """
        all_skills = self._load_active_skills()
        if skill_ids is not None:
            id_set = set(skill_ids)
            all_skills = [s for s in all_skills if s.get("id") in id_set]
        matched = self._filter_skills(all_skills, agent_name, datasource_name)
        if not matched:
            return ""
        return self.build_skill_prompt_block(matched)

    def _filter_skills(
        self, skills: List[Dict[str, Any]], agent_name: str, datasource_name: Optional[str]
    ) -> List[Dict[str, Any]]:
        result = []
        for skill in skills:
            # 检查 agent 绑定：空列表表示匹配所有 agent
            binding = skill.get("binding_agents") or []
            if binding and agent_name not in binding:
                continue
            # 检查数据源作用域
            scope_type = skill.get("scope_type", "universal")
            if scope_type == "specific" and datasource_name:
                scope_ds = skill.get("scope_datasources") or []
                if datasource_name not in scope_ds:
                    continue
            result.append(skill)
        return result

    @staticmethod
    def build_skill_prompt_block(skills: List[Dict[str, Any]]) -> str:
        """将技能列表拼接为附加到 system prompt 的文本块。"""
        parts = ["\n## 附加规则"]
        for skill in skills:
            name = skill.get("name", "未命名技能")
            instructions = skill.get("instructions", "")
            parts.append(f"\n### {name}\n{instructions}")
        return "\n".join(parts)


skill_registry = SkillRegistry()
